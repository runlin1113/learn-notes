// KaTeX 数学公式自动渲染初始化
// 需配合 arithmatex (generic: true) 与本地 katex 资源使用
document$.subscribe(function () {
  if (typeof renderMathInElement === "undefined") return;
  renderMathInElement(document.body, {
    delimiters: [
      { left: "$$", right: "$$", display: true },
      { left: "\\(", right: "\\)", display: false },
      { left: "$", right: "$", display: false },
    ],
    throwOnError: false,
  });
});
