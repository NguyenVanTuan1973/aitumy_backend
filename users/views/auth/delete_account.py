# users/views/auth/delete_account.py

from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone  # Bắt buộc phải import dòng này

from users.models import OrganizationMember, Organization


@login_required
@require_http_methods(["POST"])
@transaction.atomic
def delete_account_view(request):
    user = request.user

    try:
        # 1. Tìm thông tin tổ chức/Doanh nghiệp của User này
        member = (
            OrganizationMember.objects
            .select_related("organization")
            .filter(user=user)
            .first()
        )

        # 2. Xử lý tổ chức (Tenant) của User nếu có
        if member and member.organization:
            organization = member.organization

            # Đổi trạng thái tổ chức sang "Tạm khóa" hoặc ẩn đi thay vì xóa cứng
            organization.status = Organization.Status.SUSPENDED
            organization.is_active = False
            organization.save(update_fields=["status", "is_active"])

            # Nếu có Subscription đi kèm, hủy hiệu lực của gói luôn
            if hasattr(organization, "subscription"):
                subscription = organization.subscription
                subscription.cancel()

        # 🔥 3. HỦY KẾT NỐI VÀ XÓA CẤU HÌNH GOOGLE DRIVE CỦA USER TRÊN HỆ THỐNG
        # (Đã đưa ra ngoài độc lập: Luôn luôn chạy dù user có org hay không)
        if hasattr(user, "drive"):
            user.drive.delete()  # Bản ghi UserDrive bị xóa cứng, an toàn bảo mật cho User

        # 4. Tiến hành XÓA MỀM tài khoản User để tránh sập toàn vẹn dữ liệu
        user.is_active = False
        user.is_staff = False
        user.is_superuser = False

        # Đổi email thành một chuỗi duy nhất chứa mốc thời gian để giải phóng email gốc
        timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
        original_email = user.email
        user.email = f"deleted_{timestamp}_{original_email}"

        # Lưu thay đổi xuống Database
        user.save(update_fields=["is_active", "is_staff", "is_superuser", "email"])

        # 5. Đăng xuất, xóa bỏ hoàn toàn Session Cookie trên trình duyệt web
        logout(request)

        return JsonResponse({
            "success": True,
            "message": "Tài khoản và tổ chức liên quan đã được hủy kích hoạt thành công."
        })

    except Exception as e:
        # Nếu có bất kỳ lỗi xung đột dữ liệu nào, trả về JSON để báo cho Frontend
        return JsonResponse({
            "success": False,
            "error": f"Không thể xử lý xóa tài khoản do: {str(e)}"
        }, status=500)