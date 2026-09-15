---
title: python基础复习
date: 2026-09-13
tags: []
status: published
---


# python基础复习


# Numpy 错题整合笔记
> 适用：Python 数值计算、数组切片、广播、向量化对比

## 一、核心知识点
### 1. 数组属性 shape
- `shape` 是**属性**，不是函数！写法：`arr.shape`，❌ 不能写 `arr.shape()`
- 返回元组：一维数组 `(3,)`；二维行向量 `(1,3)`；二维数组 `(3,2)`

### 2. reshape 重塑数组
1. 重塑前后**元素总数必须相等**
2. 调用方式：`arr.reshape(行,列)`，不是 `np.reshape(行,列)`
3. reshape 返回新视图，**不会原地修改原数组，需要赋值接收**

### 3. 数组索引与切片
1. 高级索引：`arr[np.array([0,2]), :]` 选取指定多行
2. 切片左闭右开：`1:3` 取索引1、2，不含3；要取到999，写 `100:1000`
3. 布尔索引：`arr[arr>0.5]`，筛选满足条件所有元素，返回一维数组

### 4. np.newaxis 增加维度
- `arr[:, :, np.newaxis]` 在最后一维新增维度
- ⚠️ 切片操作的结果**必须赋值给变量**，否则无法后续使用这个新数组

### 5. np.max 与 keepdims
- `np.max(arr, axis=1)`：沿着列方向，取每一行最大值，会压缩维度
- `keepdims=True`：保留被压缩的维度，维持二维结构
  - 不加：shape `(3,)`；加：shape `(3,1)`
- ⚠️ max 的返回值要保存到变量，打印 shape 要打印**结果数组**，不是原数组

### 6. Numpy 广播机制
不同形状数组运算，自动扩展维度，满足广播规则才能计算
- `(3,4) + (3,1)` → `(3,4)`
- `(3,4) * (1,4)` → `(3,4)`
- `(3,3)+(1,3)` → `(3,3)`
> 广播只在维度为1的轴上扩展

### 7. 向量化 vs Python for循环
- Python 双层for循环：逐元素在Python解释器运行，速度极慢
- Numpy切片向量化：底层C实现，一次性批量运算，速度提升数百倍
- 任务：第100行 ~ 999行全部元素+5，切片写法 `x[100:1000, :] +=5`

---

## 二、错题汇总（原题+错误代码+错误原因+修正代码）
### 错题1 shape()调用错误
```python
# 错误代码
print(x.shape())
print(y.shape())

# 错误原因
shape是数组属性，不是函数，不能加括号，会报 TypeError: 'tuple' object is not callable

# 修正
print(x.shape)
print(y.shape)
```

### 错题2 arange+reshape

```
# 错误代码
a=np.arange(0,9)
a=np.reshape(5,2)

# 错误原因
1. np.arange(0,9)生成0~8共9个元素，reshape(5,2)需要10个元素，数量不匹配
2. reshape是数组方法，不能直接 np.reshape(5,2)

# 修正
a=np.arange(0,10)
b = a.reshape(5,2)
```

### 错题3 np.max keepdims 打印shape

```
# 错误代码
print(np.max(x,axis=1))
print(x.shape) # 打印原数组shape，不是max结果的shape

# 错误原因
没有保存np.max返回的数组，一直打印原始x的shape

# 修正
max1 = np.max(x,axis=1)
print(max1)
print(max1.shape)

max2 = np.max(x, axis = 1, keepdims = True)
print(max2)
print(max2.shape)
```

### 错题4 np.newaxis升维 NameError

```
# 错误代码
print(x[:, :, np.newaxis])
print("新增维度后的形状：", x_new.shape)

# 错误原因
升维结果没有赋值给x_new，变量不存在，NameError

# 修正
x_new = x[:, :, np.newaxis]
print(x_new)
print("新增维度后的形状：", x_new.shape)
```

### 错题5 广播打印顺序错误

```
# 错误代码
print(x.shape)
print()
print(y.shape)
print(z.shape) # 题目要求此处打印s.shape，错误打印z.shape

# 错误原因
输出顺序和题目评测要求不一致

# 修正
print(x.shape)
print()
print(y.shape)
print(s.shape)
print(x.shape)
print()
print(s.shape)
print(p.shape)
```

### 错题6 向量化切片（for循环对比题）

> 
> 题目：对100~999行全部元素+5

```
# 错误写法（常见坑）
x2[100:999, :] +=5 # 切片左闭右开，漏掉999行

# 修正
x2[100:1000, :] += 5
```

---

## 三、课后练习题（带参考答案）

### 练习1

```
import numpy as np
arr = np.array([[1,2,3],[4,5,6]])
# 1.打印arr形状
# 2.求每一列最大值，保留维度，打印结果和shape
```

参考答案

```
print(arr.shape)
max_col = np.max(arr, axis=0, keepdims=True)
print(max_col)
print(max_col.shape)
```

### 练习2

```
import numpy as np
# 创建0~15数组，重塑为(4,4)，取出第2行到第3行所有元素+10
a = np.arange(0,16)
b = a.reshape(4,4)
# 填写切片
```

参考答案

```
b[2:4,:] += 10
```

### 练习3 广播

```
import numpy as np
m1 = np.ones((4,5))
m2 = np.ones((4,1))
res = m1 + m2
print(res.shape)
```

参考答案

输出：`(4,5)`

### 练习4 升维

```
import numpy as np
arr = np.array([[1,2],[3,4]])
# 在第0维增加维度
arr_new = arr[np.newaxis, :, :]
print(arr_new.shape)
```

参考答案

输出：`(1,2,2)`

