class RedisKeys:
    PREFIX = "v1"

    @staticmethod
    def rpm_user(tenant_id: str, user_id: str):
        return f"{RedisKeys.PREFIX}:rl:rpm:{tenant_id}:{user_id}"
    
    @staticmethod
    def tpm_user(tenant_id: str, user_id: str):
        return f"{RedisKeys.PREFIX}:rl:tpm:{tenant_id}:{user_id}"
    
    @staticmethod
    def rpm_tenant(tenant_id: str):
        return f"{RedisKeys.PREFIX}:rl:rpm:{tenant_id}"

    @staticmethod
    def tpm_tenant(tenant_id: str):
        return f"{RedisKeys.PREFIX}:rl:tpm:{tenant_id}"
    
    @staticmethod
    def concurrency_user(tenant_id: str, user_id: str):
        return f"{RedisKeys.PREFIX}:rl:conc:{tenant_id}:{user_id}"

    @staticmethod
    def concurrency_tenant(tenant_id: str):
        return f"{RedisKeys.PREFIX}:rl:conc:{tenant_id}"