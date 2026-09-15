---
title: KNN与SVM
date: 2026-09-15
tags: []
status: published
---

# sklearn MNIST手写数字识别（KNN & SVM）实验笔记
## 知识框架

> 本次实验基于sklearn库，使用KNN与SVM(RBF高斯核)完成MNIST手写数字多分类任务。内容包含数据集介绍、算法数学原理、代码实现步骤、参数含义、调参技巧以及实验常见问题排查。
## 数据集介绍

> MNIST：Modified National Institute of Standards and Technology，机器学习入门经典手写数字灰度数据集。包含0~9共10类手写数字；图片尺寸28×28像素，展平后得到784维特征向量；数据集一共70000张样本，其中60000张训练样本，10000张测试样本。像素取值范围0~255，0代表黑色，255代表白色。

> 任务目标：输入784维像素向量，预测图片对应的手写数字类别。

## K近邻算法（KNN）

> KNN属于惰性学习算法，没有显式的模型训练过程，训练阶段只存储全部训练样本。预测时计算待预测样本与训练集内所有样本的距离，选取距离最近的k个样本进行投票，票数最多的类别作为预测结果。
> 默认距离度量为欧氏距离：
$$d(x_a,x_b)=\sqrt{\sum_{j=1}^{784}(x_{a,j}-x_{b,j})^2}$$

> 参数：n_neighbors，即k值。
> - k过小：模型容易过拟合，对噪声样本非常敏感
> - k过大：模型欠拟合，远距离样本参与投票，类别边界模糊
> 调参技巧：优先选取奇数k，避免投票平局；候选值一般取3,5,7,9；可更换曼哈顿距离对比实验效果。

## SVM支持向量机（RBF高斯核）

> 基础SVM是线性分类器，目标是寻找最优超平面，最大化两类样本之间的间隔。手写数字属于非线性分类问题，引入RBF高斯核，利用核技巧，不需要显式将样本映射到高维空间，直接在原始空间计算高维内积。
> RBF高斯核公式：
$$K(x_i,x_j)=\exp(-\gamma\|x_i-x_j\|^2)$$

> 参数：
> 1. C：惩罚系数，控制错分样本的惩罚力度。
>    - C增大：对错分样本惩罚更强，尽量减少分类错误，容易过拟合
>    - C减小：惩罚变弱，追求更大分类间隔，允许更多样本分错，容易欠拟合
> 2. gamma：高斯核带宽参数，本次实验设置`gamma="scale"`，由sklearn自动计算。
>    - gamma增大：高斯核作用范围变窄，仅邻近样本互相影响，容易过拟合
>    - gamma减小：作用范围更广，远距离样本也会互相影响，容易欠拟合
> 调参技巧：C候选范围0.1,1,10,100；gamma候选范围0.001,0.01,0.1,1；可使用GridSearchCV网格搜索自动寻找最优参数组合。

## 代码实操

> 整体实现步骤：
> 1. 导入所需依赖库
> 2. 加载MNIST数据集
> 3. 数据预处理，划分训练集、测试集
> 4. 构建KNN、SVM模型
> 5. 模型训练
> 6. 在测试集预测，计算分类准确率

> 核心代码片段
```python
from sklearn.datasets import fetch_openml
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score

# 加载MNIST数据集
mnist = fetch_openml("mnist_784", version=1, parser="auto")
# 划分训练集、测试集
X_train, X_test, y_train, y_test = train_test_split(mnist.data, mnist.target, test_size=0.2, random_state=42)

# KNN模型
knn = KNeighborsClassifier(n_neighbors=5)
knn.fit(X_train, y_train)
y_pred_knn = knn.predict(X_test)
print("KNN准确率：", accuracy_score(y_test, y_pred_knn))

# SVM RBF高斯核模型
svm = SVC(kernel="rbf", C=1.0, gamma="scale")
svm.fit(X_train, y_train)
y_pred_svm = svm.predict(X_test)
print("SVM(RBF)准确率：", accuracy_score(y_test, y_pred_svm))
```