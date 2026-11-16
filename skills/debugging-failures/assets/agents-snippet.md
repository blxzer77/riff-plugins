## Debugging

- Reproduce a reported failure before changing code, and keep the reproduction as a
  test that fails first when a test can hold it.
- Treat the reporter's guess as a hypothesis; say so when evidence contradicts it.
- Fix where the wrong state is produced, not where it surfaces. Do not widen a
  `catch`, add retries, or drop bad input to make a symptom go away.
- Check other callers of the faulty code and report who else was affected.
- Verify with the original failing command or test, and show before and after.
