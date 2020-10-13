# FAQ

-----

## Integration vs Check

A Check is any integration whose execution is triggered directly in code by the [Datadog Agent][].
Therefore, all Agent-based integrations written in Python or Go are considered Checks.

## Why test tests

We track the coverage of tests in all cases as a drop in test coverage for test code means a test function or part of it is not called. For an example see [this test bug](https://github.com/DataDog/integrations-core/pull/7714/commits/79f674ce2deb1023d73699c0a704a83f7814875d) fixed thanks to test coverage. See pyca/pynacl!290 and !4280 for more details.
