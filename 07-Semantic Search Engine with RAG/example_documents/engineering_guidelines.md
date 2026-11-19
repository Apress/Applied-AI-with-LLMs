# Engineering Guidelines

All production code should be reviewed before it is merged. Code reviews should
focus on correctness, readability, tests, and operational risk.

Automated tests are expected for new behavior. Bug fixes should include a test
that would have failed before the fix when practical.

Deployments should be small and reversible. Engineers should monitor the system
after release and roll back if user-facing errors increase.

