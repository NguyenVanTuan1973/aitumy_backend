import re
from rest_framework.exceptions import ValidationError


class UserValidators:

    @staticmethod
    def email(value: str):
        if not value or not value.strip():
            raise ValidationError("Email không được để trống")

        value = value.strip()

        regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'

        if not re.match(regex, value):
            raise ValidationError("Email không hợp lệ")

        return value.lower()

    @staticmethod
    def password(value: str):
        if not value:
            raise ValidationError("Mật khẩu không được để trống")

        if len(value) < 8:
            raise ValidationError("Mật khẩu tối thiểu 8 ký tự")

        if not re.search(r'[A-Z]', value):
            raise ValidationError("Cần ít nhất 1 chữ hoa")

        if not re.search(r'[a-z]', value):
            raise ValidationError("Cần ít nhất 1 chữ thường")

        if not re.search(r'[0-9]', value):
            raise ValidationError("Cần ít nhất 1 chữ số")

        return value

    @staticmethod
    def confirm_password(value: str, password: str):
        if not value:
            raise ValidationError("Vui lòng xác nhận mật khẩu")

        if value != password:
            raise ValidationError("Mật khẩu xác nhận không khớp")

        return value