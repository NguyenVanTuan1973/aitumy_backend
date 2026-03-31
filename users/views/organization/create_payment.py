import urllib

from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from aitumy_backend.users.models import Plan

import hashlib
import hmac
import requests
import time
import datetime

from aitumy_backend.users.views.subscription import subscription


class CreatePaymentAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        organization = getattr(request, "organization", None)

        plan_code = request.data.get("plan_code")
        method = request.data.get("method")  # momo | vnpay

        plan = Plan.objects.get(code=plan_code, is_active=True)

        amount = int(float(plan.price))  # 🔥 convert "99000.00" → 99000

        if method == "momo":
            payment_url = create_momo_payment(
                request, amount, plan_code
            )

        elif method == "vnpay":
            payment_url = create_vnpay_payment(
                request, amount, plan_code
            )

        else:
            return Response({"error": "Invalid method"}, status=400)

        return Response({
            "payment_url": payment_url
        })

class MomoIPNAPIView(APIView):
    permission_classes = []

    def post(self, request):
        data = request.data

        result_code = data.get("resultCode")

        if result_code == 0:
            # ✅ SUCCESS
            order_id = data.get("orderId")

            # 🔥 update subscription
            handle_payment_success(order_id)

        return Response({"message": "OK"})

class VNPayReturnAPIView(APIView):
    permission_classes = []

    def get(self, request):
        vnp_ResponseCode = request.GET.get("vnp_ResponseCode")

        if vnp_ResponseCode == "00":
            # ✅ SUCCESS
            handle_payment_success(request.GET.get("vnp_TxnRef"))

        return Response({"message": "OK"})

def create_momo_payment(request, amount, plan_code):
    order_id = str(int(time.time()))
    request_id = order_id

    order_info = f"Upgrade {plan_code}"
    redirect_url = "https://yourdomain.com/payment/return/"
    ipn_url = "https://yourdomain.com/api/payment/momo-ipn/"

    raw = (
        f"accessKey={settings.MOMO_ACCESS_KEY}"
        f"&amount={amount}"
        f"&extraData="
        f"&ipnUrl={ipn_url}"
        f"&orderId={order_id}"
        f"&orderInfo={order_info}"
        f"&partnerCode={settings.MOMO_PARTNER_CODE}"
        f"&redirectUrl={redirect_url}"
        f"&requestId={request_id}"
        f"&requestType=captureWallet"
    )

    signature = hmac.new(
        settings.MOMO_SECRET_KEY.encode(),
        raw.encode(),
        hashlib.sha256
    ).hexdigest()

    payload = {
        "partnerCode": settings.MOMO_PARTNER_CODE,
        "accessKey": settings.MOMO_ACCESS_KEY,
        "requestId": request_id,
        "amount": str(amount),
        "orderId": order_id,
        "orderInfo": order_info,
        "redirectUrl": redirect_url,
        "ipnUrl": ipn_url,
        "extraData": "",
        "requestType": "captureWallet",
        "signature": signature,
        "lang": "vi"
    }

    res = requests.post(settings.MOMO_ENDPOINT, json=payload).json()

    return res.get("payUrl")

def create_vnpay_payment(request, amount, plan_code):
    vnp_params = {
        "vnp_Version": "2.1.0",
        "vnp_Command": "pay",
        "vnp_TmnCode": settings.VNPAY_TMN_CODE,
        "vnp_Amount": amount * 100,
        "vnp_CurrCode": "VND",
        "vnp_TxnRef": str(int(time.time())),
        "vnp_OrderInfo": f"Upgrade {plan_code}",
        "vnp_OrderType": "billpayment",
        "vnp_Locale": "vn",
        "vnp_ReturnUrl": "https://yourdomain.com/payment/vnpay-return/",
        "vnp_IpAddr": "127.0.0.1",
        "vnp_CreateDate": datetime.datetime.now().strftime('%Y%m%d%H%M%S'),
    }

    sorted_params = sorted(vnp_params.items())
    query = urllib.parse.urlencode(sorted_params)

    hash_data = "&".join([f"{k}={v}" for k, v in sorted_params])

    secure_hash = hmac.new(
        settings.VNPAY_HASH_SECRET.encode(),
        hash_data.encode(),
        hashlib.sha512
    ).hexdigest()

    payment_url = f"{settings.VNPAY_URL}?{query}&vnp_SecureHash={secure_hash}"

    return payment_url

def handle_payment_success(order_id):
    # TODO: map order_id → user → plan

    subscription.status = "active"
    subscription.save()