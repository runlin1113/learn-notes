---
title: Markdown 写作速查
---

# Markdown 写作速查

本站基于 MkDocs Material，支持标准 Markdown 及大量增强语法。
以下是常用功能的一页速查——**照着抄就行**。

## 1. 文件头（frontmatter）

每个 `.md` 文件顶部用 `---` 包裹的几行叫文件头，用来声明元信息：

```yaml
---
title: 一篇示例笔记   # 页面标题（不写则取第一个 # 标题）
date: 2026-09-05      # 写作日期
tags: [数学, 极限]    # 标签（可多个）
status: published     # published=已发布 / draft=草稿
---
```

`note new` 命令会为你自动生成文件头，无需手写。

## 2. 数学公式（KaTeX）

行内公式用 `$...$`，独立公式用 `$$...$$`：

- 行内：质能方程 $E=mc^2$ 是物理学最著名的公式。
- 独立：
$$
\int_{-\infty}^{+\infty} e^{-x^2}\,\mathrm{d}x = \sqrt{\pi}
$$

## 3. 代码块（语法高亮 + 复制按钮）

````markdown
```python
def hello(name: str) -> str:
    """示例：三引号注释"""
    return f"Hello, {name}!"
```
````

效果：

```python
def hello(name: str) -> str:
    """示例：三引号注释"""
    return f"Hello, {name}!"
```

## 4. 提示框（Admonition）

```markdown
!!! note "小标题"
    这是普通提示框的内容。

!!! tip "技巧"
    这是技巧提示框。

!!! warning "注意"
    这是警告提示框，用于提醒容易出错的地方。

!!! danger "危险"
    用于严重错误 / 高风险操作的提醒。

!!! info "信息"
    一般信息说明。
```

!!! note "小标题"
    这是普通提示框的内容。

!!! tip "技巧"
    这是技巧提示框。

!!! warning "注意"
    这是警告提示框，用于提醒容易出错的地方。

!!! danger "危险"
    用于严重错误 / 高风险操作的提醒。

!!! info "信息"
    一般信息说明。

还可以用 `???` 做成可折叠：

```markdown
??? question "点击展开看答案"
    藏在折叠框里的详细解释。
```

??? question "点击展开看答案"
    藏在折叠框里的详细解释。

## 5. 多标签页（不同框架/语言对照）

````markdown
=== "PyTorch"

    ```python
    import torch
    x = torch.tensor([1.0, 2.0])
    ```

=== "NumPy"

    ```python
    import numpy as np
    x = np.array([1.0, 2.0])
    ```
````

=== "PyTorch"

    ```python
    import torch
    x = torch.tensor([1.0, 2.0])
    ```

=== "NumPy"

    ```python
    import numpy as np
    x = np.array([1.0, 2.0])
    ```

## 6. 表格

```markdown
| 概念 | 英文 | 说明 |
|:----|:----:|:----|
| 梯度 | Gradient | 多元函数对各变量偏导组成的向量 |
| 损失 | Loss | 预测与真值的差距度量 |
```

| 概念 | 英文 | 说明 |
|:----|:----:|:----|
| 梯度 | Gradient | 多元函数对各变量偏导组成的向量 |
| 损失 | Loss | 预测与真值的差距度量 |

## 7. 任务清单

```markdown
- [x] 已完成的事情
- [ ] 待办事项 A
- [ ] 待办事项 B
```

- [x] 已完成的事情
- [ ] 待办事项 A
- [ ] 待办事项 B

## 8. 图片与链接

```markdown
![图片说明文字](../../assets/images/example.png)

[链接文字](https://example.com)
```

图片请放在 `docs/assets/images/` 目录中。

## 9. 更多语法

- **加粗**、*斜体*、`行内代码`、~~删除线~~、++insert++、^上标^、~下标~ 都可直接使用；
- 脚注示例：[^1]

[^1]: 这是脚注的内容，会显示在页面底部。
