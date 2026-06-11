# case-002-pattern-match: 已知模式命中

## 输入
```yaml
错误信息: |
  Traceback ... AttributeError: 'CheckItem' object has no attribute 'get'
  File ".../cli.py", line 165, in cmd_health
源代码: |
  print(f"  [{d.get('category', '?')}] {d.get('check', {}).get('text', '')[:60]}")
```

## 期望输出检查

### 内容检查
- [ ] 出现了 "AttributeError"
- [ ] 出现了 "CheckItem"
- [ ] 出现了 ".text"
