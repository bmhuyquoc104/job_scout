from job_scout.core.rate_limit import RateLimiter


def test_one_call_per_key_per_interval() -> None:
    limiter = RateLimiter(60)

    assert limiter.allow("a")
    assert not limiter.allow("a")
    assert limiter.allow("b")  # keys are independent
    assert limiter.allow("a", interval=0)  # a per-call interval overrides the default
