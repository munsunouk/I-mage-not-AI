async function writeClipboard(text) {
  if (navigator.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (error) {
      /* fall through to the selection API */
    }
  }
  const area = document.createElement("textarea");
  area.value = text;
  area.setAttribute("readonly", "");
  area.style.position = "fixed";
  area.style.top = "0";
  area.style.left = "0";
  area.style.opacity = "0";
  document.body.appendChild(area);
  area.focus();
  area.select();
  let ok = false;
  try {
    ok = document.execCommand("copy");
  } catch (error) {
    ok = false;
  }
  area.remove();
  return ok;
}

document.querySelectorAll("button.copy").forEach((button) => {
  const label = button.textContent;
  button.addEventListener("click", async () => {
    const source = document.getElementById(button.getAttribute("data-copy"));
    const text = source ? source.innerText : "";
    button.textContent = "Copying…";
    const ok = await writeClipboard(text);
    button.textContent = ok ? "Copied" : "Copy failed";
    window.setTimeout(() => {
      button.textContent = label;
    }, 2000);
  });
});
