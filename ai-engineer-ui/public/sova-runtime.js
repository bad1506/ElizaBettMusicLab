(() => {
  const replacements = new Map([
    ["Eliza Bett Music Lab", "SØNA"],
    ["Eliza Bett\nMusic Lab", "SØNA"],
    ["Eliza Bett", "SØNA"],
  ]);
  const normalize = (root) => {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    for (const node of nodes) {
      let value = node.nodeValue || "";
      for (const [from, to] of replacements) value = value.split(from).join(to);
      if (value !== node.nodeValue) node.nodeValue = value;
    }
  };
  const boot = () => {
    if (!document.body) return;
    normalize(document.body);
    new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        for (const node of mutation.addedNodes) if (node.nodeType === Node.ELEMENT_NODE) normalize(node);
        if (mutation.type === "characterData") normalize(mutation.target.parentElement || document.body);
      }
    }).observe(document.body, { childList: true, subtree: true, characterData: true });
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot, { once: true }); else boot();
})();
