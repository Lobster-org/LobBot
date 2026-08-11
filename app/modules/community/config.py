VERIFICATION_POLL_SECONDS = 30
VERIFICATION_BATCH_SIZE = 100
VERIFICATION_CLAIM_TIMEOUT_SECONDS = 5 * 60

SUPPORTED_TEMPLATE_FIELDS = frozenset(
    {
        "name",
        "first_name",
        "username",
        "mention",
        "group",
        "member_count",
    }
)
