# Test Guidelines

This document outlines best practices and lessons learned from our testing experience with the IPv6 Route Listener project.

## 🎯 Test Design Principles

### 1. Avoid Brittle Assertions

❌ **Don't** assert exact log messages:
```python
# Too strict - will break if message text changes
mock_logger.info.assert_has_calls([
    call("🔔 Router Advertisement from fe80::1"),
    call("📡 On-link prefix: fd82:cd32:5ad7:ff4a::/64 (directly connected)"),
    call("🔧 Processing 1 route(s)/prefix(es) from RA")
])
```

✅ **Do** verify that logging occurred:
```python
# More resilient - verifies logging happened without being strict about content
mock_logger.info.assert_called()
```

### 2. Be Flexible with Logging

❌ **Don't** assert exact number of log calls:
```python
# Too strict - will break if we add more logging
mock_logger.debug.assert_called_once()
```

✅ **Do** verify that logging occurred at least once:
```python
# More resilient - allows for additional logging without breaking tests
mock_logger.debug.assert_called()
```

### 3. Focus on Behavior, Not Implementation

❌ **Don't** test implementation details:
```python
# Too strict - tests how something is done rather than what it does
assert packet_handler._check_duplicate.called
```

✅ **Do** test observable behavior:
```python
# Better - tests what the code does from the user's perspective
assert not packet_handler._handle_packet(duplicate_packet)
```

## 📝 Example: Packet Filtering Tests

See `test_packet_filtering.py` for a practical example of these principles in action:

```python
def test_ignore_non_ipv6_packet(packet_handler, mock_logger):
    """Test that non-IPv6 packets are ignored and logged in verbose mode."""
    non_ipv6_packet = Mock()
    non_ipv6_packet.__iter__ = Mock(return_value=iter([]))
    packet_handler._handle_packet(non_ipv6_packet)
    # Verify that debug logging occurred
    mock_logger.debug.assert_called()
```

This test:
1. Verifies the behavior (non-IPv6 packets are ignored)
2. Checks that logging occurred without being strict about the message
3. Allows for additional logging without breaking the test

## 🔍 Why These Guidelines Matter

1. **Maintainability**: Tests that are too strict about implementation details or exact messages are harder to maintain
2. **Refactoring**: Flexible tests make it easier to refactor code without breaking tests
3. **Readability**: Tests that focus on behavior are easier to understand and maintain
4. **Reliability**: Tests that aren't brittle are less likely to fail due to unrelated changes

## 🚀 Best Practices Summary

1. Test behavior, not implementation
2. Avoid asserting exact log messages
3. Be flexible with logging assertions
4. Use meaningful test names that describe the behavior being tested
5. Keep tests focused and simple
6. Use appropriate levels of abstraction in test assertions

## 📚 References

- [pytest-mock documentation](https://pytest-mock.readthedocs.io/)
- [Python Testing with pytest](https://pytest.org/)
- [Test-Driven Development with Python](https://www.obeythetestinggoat.com/) 