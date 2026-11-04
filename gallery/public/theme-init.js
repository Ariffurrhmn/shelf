// Runs before first paint so the page never flashes the wrong theme.
(function () {
  try {
    var saved = localStorage.getItem("shelf-theme");
    var dark = saved ? saved === "dark" : window.matchMedia("(prefers-color-scheme: dark)").matches;
    document.documentElement.classList.toggle("dark", dark);
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", dark ? "#181a20" : "#fafaf8");
  } catch (e) {}
})();
