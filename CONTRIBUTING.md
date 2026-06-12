# 贡献指南

## 提 issue
- Bug：描述现象、复现步骤、期望行为
- 新功能：描述场景、为什么需要、建议方案
- 技能包：分享你做的技能包

## 提 PR
1. Fork 仓库
2. 在分支上修改：`git checkout -b feat/xxx`
3. 跑全部测试：`python3 engine/test_*.py && python3 engine/test_constitution.py`
4. 如果新增技能，加 `.gitignore` 排除不推
5. 提交消息用中文或英文均可

## 技能包规范
技能包是一个独立目录，结构：
```
skills/[技能名]/
├── SKILL.md       # 操作规范
├── .memory.md     # 踩坑记录
├── config.json    # 注册元信息
└── tests/         # 测试用例
```
