# case-001-classify: 错误分类能力

## 输入
```yaml
错误信息: "SyntaxError: invalid syntax. Perhaps you forgot a comma?"
源代码: |
  print(f"Hello" "World")
```

## 期望输出检查

### 结构检查
- [ ] 出现了 "分类"
- [ ] 出现了 "根因"
- [ ] 出现了 "修复"

### 内容检查
- [ ] 出现了 "语法错误"
- [ ] 出现了 "行号"
