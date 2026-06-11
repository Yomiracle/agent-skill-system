# case-003-root-cause: 根因定位

## 输入
```yaml
错误信息: |
  File ".../searcher.py", line 86, in _score
    keyword_hits += 0.3
  UnboundLocalError: local variable 'keyword_hits' referenced before assignment
源代码: |
  def _score(self, task_lower, entry, cfg):
      for kw in cfg.trigger_keywords:
          ...
          keyword_hits += 0.3
      if keyword_hits > 0:
          score += min(keyword_hits * 30, 90)
```

## 期望输出检查

### 内容检查
- [ ] 出现了 "keyword_hits"
- [ ] 出现了 "初始化"
- [ ] 出现了 "行" 或 "line"
