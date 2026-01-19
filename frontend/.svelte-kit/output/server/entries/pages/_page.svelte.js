import { x as attr, y as ensure_array_like, z as attr_class } from "../../chunks/index.js";
import { a as ssr_context, e as escape_html } from "../../chunks/context.js";
import "clsx";
function onDestroy(fn) {
  /** @type {SSRContext} */
  ssr_context.r.on_destroy(fn);
}
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let uploads = [];
    let current = null;
    let uploading = false;
    function fmtDate(d) {
      return new Date(d).toLocaleString();
    }
    onDestroy(() => {
    });
    $$renderer2.push(`<div class="layout svelte-1uha8ag"><aside class="sidebar svelte-1uha8ag"><div class="sidebarHeader svelte-1uha8ag"><div class="title svelte-1uha8ag">Listen</div> <button class="btn">Prompts</button></div> <form class="uploadForm svelte-1uha8ag"><label class="label svelte-1uha8ag" for="fileInput">Upload audio</label> <input id="fileInput" class="input" name="file" type="file" accept="audio/*" required/> <div class="row svelte-1uha8ag"><label class="check svelte-1uha8ag"><input type="checkbox" name="summarize" value="true"/> Summarize</label> <label class="check svelte-1uha8ag"><input type="checkbox" name="action_items" value="true"/> Action items</label></div> <input class="input" name="display_name" placeholder="Name (optional)"/> <input class="input" name="llm_model" placeholder="LLM model (optional)"/> <button class="btn primary"${attr("disabled", uploading, true)}>${escape_html("Upload & queue")}</button> `);
    {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]--></form> <div class="list svelte-1uha8ag"><div class="listHeader svelte-1uha8ag">Library</div> <!--[-->`);
    const each_array = ensure_array_like(uploads);
    for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
      let u = each_array[$$index];
      $$renderer2.push(`<div${attr_class("item svelte-1uha8ag", void 0, { "active": current?.id === u.id })}><button class="itemMain svelte-1uha8ag"><div class="itemName svelte-1uha8ag">${escape_html(u.display_name)}</div> <div class="itemMeta muted svelte-1uha8ag">${escape_html(fmtDate(u.created_at))}</div></button> <button class="btn danger">Del</button></div>`);
    }
    $$renderer2.push(`<!--]--></div></aside> <main class="main svelte-1uha8ag">`);
    {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]--> `);
    {
      $$renderer2.push("<!--[!-->");
      $$renderer2.push(`<div class="empty svelte-1uha8ag"><div class="h1 svelte-1uha8ag">Upload audio to begin</div> <div class="muted">Files are queued in RabbitMQ and processed by the worker.</div></div>`);
    }
    $$renderer2.push(`<!--]--></main></div> `);
    {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]-->`);
  });
}
export {
  _page as default
};
