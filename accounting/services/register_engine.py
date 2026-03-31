from .registers.hkd.s1a_register import S1aRegister
from .registers.hkd.s1b_register import S1bRegister
from .registers.hkd.s2a_register import S2aRegister
from .registers.hkd.s2b_register import S2bRegister
from .registers.hkd.s2c_register import S2cRegister
from .registers.hkd.s2d_register import S2dRegister
from .registers.hkd.s2e_register import S2eRegister
from .registers.hkd.s3a_register import S3aRegister


class RegisterEngine:

    REGISTERS = {
        "S1a-HKD": S1aRegister,
        "S1b-HKD": S1bRegister,
        "S2a-HKD": S2aRegister,
        "S2b-HKD": S2bRegister,
        "S2c-HKD": S2cRegister,
        "S2d-HKD": S2dRegister,
        "S2e-HKD": S2eRegister,
        "S3a-HKD": S3aRegister,
    }

    @classmethod
    def get_register(cls, form_code):

        register_class = cls.REGISTERS.get(form_code)

        if not register_class:
            raise Exception(f"Register {form_code} not supported")

        return register_class()