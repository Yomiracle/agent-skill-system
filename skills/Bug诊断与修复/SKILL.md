# Bug诊断与修复

## 目标
对Python代码中的bug进行系统性诊断：读取错误信息→定位根因→生成修复→验证修复→输出可落地的改法文本。

## 适用场景
**正向触发：**
- 运行代码后报错（SyntaxError/AttributeError/TypeError/NameError/IndexError 等）
- 测试失败，输出不匹配预期
- 用户要求「debug」「帮我看看哪里错了」「为什么跑不通」

**排除条件：**
- 非Python语言的bug
- 纯逻辑设计讨论（没有具体的运行错误）
- 性能优化/重构（不是bug驱动）

## 输入
- **错误信息** (必填)：完整的 traceback 或测试失败输出
- **源代码** (必填)：出错的 .py 文件内容
- **上下文** (可选)：运行环境、相关依赖

## 输出
输出应包含：
1. 错误分类（语法/逻辑/环境/数据流）
2. 根因定位（精确到行号）
3. 修复方案（可直接粘贴的改后代码）
4. 验证步骤

## 流程

### 步骤1：错误分类
根据错误类型分四类：
- **语法错误**：SyntaxError, IndentationError, 拼写错误
- **逻辑错误**：AssertionError, 输出与预期不符, 变量污染
- **环境错误**：ModuleNotFoundError, command not found, 路径问题
- **数据流错误**：AttributeError, NameError, NoneType has no attribute

- 检查点：分类明确，不张冠李戴

### 步骤2：根因定位
- 从 traceback 最后一行往上追踪，找到**我方代码的第一个调用点**
- 不追库代码（site-packages/ 中的调用不追）
- 读取报错行及其上下3行

- 检查点：定位精确到行号+变量名

### 步骤3：同类模式匹配
对照已知失效模式库，判断当前bug是否属于已记录的模式：
- 模式A：re.match 当 re.search 用
- 模式B：变量跨测试污染
- 模式C：f-string 中中文引号冲突
- 模式D：check.passed 未回写
- 模式E：python 路径（py vs python3）
- 模式F：字符串替换不匹配（\uXXXX escape 问题）

- 检查点：如命中已知模式，直接复用对应对策

### 步骤4：生成修复
- 输出改前的代码片段（3-5行上下文）
- 输出改后的代码片段（可直接粘贴）
- 说明为什么这样改

- 检查点：修复后代码的缩进与原文件一致

### 步骤5：验证指导
- 给出复测命令（如 `python3 engine/test_c2_runner.py`）
- 提醒检查其他可能受影响的位置

## 规则清单

### 诊断规范
- 【必须】先分类再定位，不要看到错误就改
- 【必须】区分「根因」和「表面错误」——traceback最后一行通常是表面错误
- 【禁止】不得跨行修改未涉及的错误（不要顺手改其他东西引入新bug）
- 【建议】修改前先备份原文件或至少确认 git 状态干净

### 修复规范
- 【必须】修复后给出可粘贴的改后代码（old_string → new_string 格式）
- 【必须】修复后给出复测命令
- 【禁止】不得修改库代码
- 【建议】对同类错误做全局搜索，一处发现多处修复

### 验证规范
- 【必须】跑原始复现命令确认不再报同错
- 【建议】跑相关测试文件的全部用例（防止修复引入回归）

## 已知失效模式

### 模式A：re.match vs re.search 混淆
- 描述：`re.match` 只匹配行首。当断言文本前有其他内容时，`match` 返回 None，导致模式跳过
- 识别：正则模式明明正确但匹配失败
- 对策：需要在整个字符串中搜索时用 `re.search`，需要行首锚定才用 `re.match`

### 模式B：变量跨测试污染
- 描述：集成测试中前一步创建的临时目录/变量被后一步复用，导致后一步的断言被污染
- 识别：单测通过但集成测试挂，或者测试顺序敏感
- 对策：每个独立测试用例使用独立变量名和独立临时目录

### 模式C：f-string 中文引号冲突
- 描述：中文「」「」和英文引号在 f-string 中混用，Python 解析器误判字符串边界
- 识别：`SyntaxError: invalid syntax` 指向 f-string 行，但肉眼看不出来
- 对策：中文引号用变量替代，或用 `'单引号'` 分隔 f-string 外层

### 模式D：check.passed 未回写
- 描述：`_evaluate` 方法只返回 bool，没有写到 `check.passed` 属性
- 识别：测试输出中所有检查都显示为未执行状态
- 对策：`_check_assertion` 中显式写 `check.passed = result`

### 模式E：python vs python3
- 描述：macOS 默认 `python` 不存在，只有 `python3`
- 识别：`command not found: python`
- 对策：统一使用 `python3`

### 模式F：字符串匹配中的转义陷阱
- 描述：`\uXXXX` 转义序列在 Python 字符串和正则模式中行为不同
- 识别：`Edit` 工具报告 "String to replace not found" 但肉眼看来字符串一致
- 对策：用 Python 脚本直接读取并替换，绕过转义匹配问题

## 参考
- Python traceback 文档
- 正则表达式 `re` 模块文档
- pytest 测试输出格式
