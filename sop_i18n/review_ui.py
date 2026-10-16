"""Local browser review UI for P3 candidates and P2 translation memory."""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from typing import Any

from .candidates import TranslationCandidate, candidates_payload, load_candidates
from .glossary import Glossary
from .jobs import TranslationJob, load_jobs
from .memory import TranslationMemory
from .models import Placeholder, Segment
from .qa import validate_candidate
from .review import approve
from .terminology import extract_term_candidates


HTML = r'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SOP Translation Review</title>
<style>
:root{color-scheme:dark;--bg:#10131a;--panel:#181d27;--line:#2d3748;--muted:#9aa6b8;--accent:#65d6b3;--warn:#f3bd68;--bad:#f17c8a}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:#edf2f7;font:14px system-ui,-apple-system,Segoe UI,sans-serif}button,input,textarea{font:inherit;color:inherit}button{border:1px solid var(--line);background:#202938;border-radius:7px;padding:9px 13px;cursor:pointer}button:hover{border-color:var(--accent)}button.primary{background:#176b59;border-color:#2cae8d}button.warn{background:#745324;border-color:#c79143}.app{display:grid;grid-template-columns:330px 1fr;min-height:100vh}.side{border-right:1px solid var(--line);padding:20px;overflow:auto}.main{padding:28px;max-width:1200px;width:100%}h1{font-size:22px;margin:0 0 6px}h2{font-size:17px;margin:0 0 14px}.muted{color:var(--muted)}.counts{display:flex;gap:8px;flex-wrap:wrap;margin:18px 0}.pill{padding:5px 8px;border-radius:99px;background:#242c3a;color:var(--muted)}.pill.bad{color:#ffadb5}.pill.ok{color:#a7f3d0}.filters{display:flex;gap:8px;margin:14px 0}.filters button{padding:6px 8px;font-size:12px}.item{display:block;width:100%;text-align:left;padding:11px;margin:5px 0;background:transparent}.item.selected{border-color:var(--accent);background:#1b2c2e}.item .source{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.item .meta{font-size:11px;color:var(--muted);margin-top:5px}.editor{display:grid;gap:16px}.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:18px}.source{white-space:pre-wrap;line-height:1.65}.target{width:100%;min-height:150px;resize:vertical;background:#111722;border:1px solid var(--line);border-radius:7px;padding:13px;line-height:1.7}.actions{display:flex;gap:10px;flex-wrap:wrap}.issue{border-left:3px solid var(--bad);padding:8px 10px;margin:6px 0;background:#291c25}.issue.warn{border-color:var(--warn)}.context{display:grid;grid-template-columns:1fr 1fr;gap:10px}.context div{background:#111722;border-radius:7px;padding:10px}.toast{position:fixed;right:22px;bottom:20px;background:#243344;padding:12px 16px;border-radius:8px;display:none}.empty{padding:60px 20px;text-align:center;color:var(--muted)}
</style></head><body><div class="app"><aside class="side"><h1>SOP 审核</h1><div class="muted">P3 candidate → P2 TM</div><div id="counts" class="counts"></div><div class="filters"><button onclick="setFilter('all')">全部</button><button onclick="setFilter('fail')">需修正</button><button onclick="setFilter('draft')">已导入</button></div><div id="list"></div></aside><main class="main"><div id="editor" class="empty">加载中…</div></main></div><div id="toast" class="toast"></div>
<script>
let state={items:[],filter:'candidate',selected:null};
async function api(path,opts){let r=await fetch(path,opts);let d=await r.json();if(!r.ok)throw Error(d.error||'请求失败');return d}
function esc(s){return String(s??'').replace(/[&<>"']/g,x=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[x]))}
function setFilter(f){state.filter=f;renderList()}
function show(msg){let t=document.getElementById('toast');t.textContent=msg;t.style.display='block';setTimeout(()=>t.style.display='none',2500)}
function render(){let c=state.items.reduce((a,x)=>(a[x.status]=(a[x.status]||0)+1,a),{});document.getElementById('counts').innerHTML=Object.entries(c).map(([k,v])=>`<span class="pill ${k==='fail'?'bad':k==='approved'?'ok':''}">${k}: ${v}</span>`).join('');renderList();renderEditor()}
function renderList(){let xs=state.items.filter(x=>state.filter==='all'||state.filter==='fail'&&x.qa==='fail'||state.filter==='draft'&&['draft','approved'].includes(x.status));document.getElementById('list').innerHTML=xs.map(x=>`<button class="item ${x.job_id===state.selected?'selected':''}" onclick="selectItem('${x.job_id}')"><div class="source">${esc(x.source_text.replace(/\[\[\[.*?\]\]\]/g,'…'))}</div><div class="meta">${x.status} · QA ${x.qa} · ${x.job_id}</div></button>`).join('')||'<div class="muted">没有匹配项</div>'}
function selectItem(id){state.selected=id;renderList();renderEditor()}
function renderEditor(){let x=state.items.find(x=>x.job_id===state.selected);let e=document.getElementById('editor');if(!x){e.innerHTML='<div class="empty">从左侧选择一条译文</div>';return}let issues=(x.issues||[]).map(i=>`<div class="issue ${i.severity==='warning'?'warn':''}"><b>${esc(i.code)}</b> ${esc(i.message)}</div>`).join('');e.className='editor';e.innerHTML=`<div><h2>${esc(x.job_id)}</h2><div class="muted">状态：${esc(x.status)}　QA：${esc(x.qa)}　source key：${esc(x.source_key)}</div></div><section class="card"><h2>原文（placeholder 受保护）</h2><div class="source">${esc(x.source_text)}</div></section><section class="card"><h2>译文</h2><textarea id="target" class="target">${esc(x.target)}</textarea><div class="actions" style="margin-top:12px"><button onclick="save(false)">保存候选</button><button class="primary" onclick="save(true)">保存并导入 draft</button><button class="warn" onclick="approveItem()">审核通过并批准</button></div></section><section class="card"><h2>QA 结果</h2>${issues||'<div class="muted">当前没有 QA 问题</div>'}</section><section class="card"><h2>上下文</h2><div class="context"><div><b>章节</b><br>${esc((x.context?.headings||[]).join(' / ')||'—')}</div><div><b>上一段</b><br>${esc(x.context?.previous_text||'—')}</div><div><b>下一段</b><br>${esc(x.context?.next_text||'—')}</div></div></section>`}
async function save(importDraft){try{let x=state.items.find(x=>x.job_id===state.selected);let target=document.getElementById('target').value;let d=await api('/api/item/'+x.job_id,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({target,action:importDraft?'draft':'save'})});show(d.message);await refresh()}catch(e){show('保存失败：'+e.message)}}
async function approveItem(){try{let x=state.items.find(x=>x.job_id===state.selected);let target=document.getElementById('target').value;if(!confirm('确认将此译文批准为 approved？'))return;let d=await api('/api/item/'+x.job_id,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({target,action:'approve',reviewer:'local-ui'})});show(d.message);await refresh()}catch(e){show('批准失败：'+e.message)}}
async function refresh(){let old=state.selected;let filter=state.filter||'candidate';state=await api('/api/state');state.filter=filter;state.selected=old&&state.items.some(x=>x.job_id===old)?old:(state.items[0]?.job_id||null);render()}
const side=document.querySelector('.side');side.style.height='100vh';side.style.overflowY='scroll';side.style.overflowX='hidden';side.style.position='sticky';side.style.top='0';document.querySelector('.filters').insertAdjacentHTML('beforeend','<button onclick="setFilter(\'candidate\')">candidate</button>');const baseRenderList=renderList;renderList=function(){if(state.filter!=='candidate'){baseRenderList();return}let xs=state.items.filter(x=>x.status==='candidate');document.getElementById('list').innerHTML=xs.map(x=>`<button class="item ${x.job_id===state.selected?'selected':''}" onclick="selectItem('${x.job_id}')"><div class="source">${esc(x.source_text.replace(/\[\[\[.*?\]\]\]/g,'…'))}</div><div class="meta">${x.status} · QA ${x.qa} · ${x.job_id}</div></button>`).join('')||'<div class="muted">没有匹配项</div>'};
async function showTerms(){let xs=state.term_candidates||[];document.getElementById('editor').className='editor';document.getElementById('editor').innerHTML='<div><h2>术语候选</h2><div class="muted">自动提取结果不会自动写入 glossary，请逐条确认中文译法。</div></div>'+ (xs.map(x=>`<section class="card"><h2>${esc(x.source)}</h2><div class="muted">出现 ${x.count} 次 · ${x.job_ids.join(', ')}</div><div class="actions" style="margin-top:10px"><input id="term-${esc(x.source)}" placeholder="中文译法" style="flex:1;min-width:220px;background:#111722;border:1px solid var(--line);border-radius:7px;padding:9px"><button class="primary" onclick="addTerm('${esc(x.source).replace(/'/g,"\\'")}')">加入 glossary</button></div></section>`).join('')||'<div class="empty">没有新的术语候选</div>');}
async function addTerm(source){try{let input=document.getElementById('term-'+source);let d=await api('/api/terms',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({source,target:input.value})});show(d.message);await refresh();showTerms()}catch(e){show('术语保存失败：'+e.message)}}
document.querySelector('.filters').insertAdjacentHTML('beforeend','<button onclick="showTerms()">术语候选</button>');
refresh().catch(e=>show(e.message));
</script></body></html>'''


class ReviewApp:
    def __init__(self, jobs_path: Path, candidates_path: Path, memory_path: Path, glossary_path: Path) -> None:
        self.jobs_path, self.candidates_path, self.memory_path, self.glossary_path = jobs_path, candidates_path, memory_path, glossary_path
        self.lock = threading.RLock()

    def _load(self) -> tuple[list[TranslationJob], list[TranslationCandidate], TranslationMemory, Glossary]:
        return load_jobs(json.loads(self.jobs_path.read_text(encoding="utf-8"))), load_candidates(json.loads(self.candidates_path.read_text(encoding="utf-8"))), TranslationMemory.load(self.memory_path), Glossary.load(self.glossary_path)

    @staticmethod
    def _segment(job: TranslationJob) -> Segment:
        placeholders = tuple(Placeholder.from_dict(item) for item in job.source_placeholders)
        return Segment(job.segment_id, job.source_text, "", (), job.node_type, job.context, placeholders)

    def state(self) -> dict[str, Any]:
        jobs, candidates, memory, glossary = self._load(); by_id = {x.job_id: x for x in candidates}; result=[]
        for job in jobs:
            candidate = by_id.get(job.job_id)
            if not candidate: continue
            records = [r for r in memory.records if r.source_key == job.source_key and r.language == memory.language]
            record = next((r for r in records if r.occurrence_id in job.occurrence_ids or not r.occurrence_id), None)
            approved = next((r for r in records if r.status == "approved" and r.target), None)
            # A repeated source key is already represented by the library TM.
            # It must not remain actionable as a new candidate merely because
            # its occurrence ID differs from the existing record.
            status = record.status if record else ("duplicate" if approved else "candidate")
            result.append({"job_id": job.job_id, "segment_id": job.segment_id, "source_key": job.source_key, "source_text": job.source_text, "target": candidate.target, "context": job.context, "qa": (candidate.validation or {}).get("status", "pending"), "issues": (candidate.validation or {}).get("issues", []), "status": status, "record_id": record.record_id if record else (approved.record_id if approved else None)})
        return {"items": result, "total": len(result), "term_candidates": extract_term_candidates(jobs, glossary, limit=300)}

    def add_term(self, source: str, target: str) -> dict[str, Any]:
        source, target = source.strip(), target.strip()
        if not source or not target: raise ValueError("source 和 target 不能为空")
        with self.lock:
            payload = json.loads(self.glossary_path.read_text(encoding="utf-8")); terms = payload.setdefault("terms", [])
            if any(item.get("source", "").casefold() == source.casefold() for item in terms): raise ValueError("术语已存在")
            term_id = "term-" + "-".join(source.casefold().split())
            terms.append({"id": term_id, "source": source, "target": target, "match_mode": "phrase", "severity": "warning"})
            temporary = self.glossary_path.with_suffix(self.glossary_path.suffix + ".tmp")
            temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"); temporary.replace(self.glossary_path)
        return {"message": "术语已加入 glossary"}

    def update(self, job_id: str, target: str, action: str, reviewer: str) -> dict[str, Any]:
        with self.lock:
            jobs, candidates, memory, glossary = self._load(); job = next((x for x in jobs if x.job_id == job_id), None); candidate = next((x for x in candidates if x.job_id == job_id), None)
            if not job or not candidate: raise ValueError("Unknown job ID")
            approved = next((r for r in memory.records if r.source_key == job.source_key and r.language == memory.language and r.status == "approved" and r.target), None)
            if approved and action in {"draft", "approve"}:
                # This candidate is a duplicate occurrence, not a new TM
                # decision. Keep the artifact for traceability, but make the
                # operation idempotent and let state() classify it as duplicate.
                self._save_candidates(candidates)
                return {"message": "该原文已有 approved 译文，已跳过重复候选"}
            existing = next((r for r in memory.records if r.source_key == job.source_key and (r.occurrence_id in job.occurrence_ids or not r.occurrence_id)), None)
            if existing and existing.status == "approved": raise ValueError("approved 记录受保护，不能在 UI 中修改")
            candidate.target = target
            issues = validate_candidate(candidate, job, glossary)
            candidate.validation = {"status": "pass" if not any(x.severity == "error" for x in issues) else "fail", "issues": [x.to_dict() for x in issues]}
            if action in {"draft", "approve"}:
                if candidate.validation["status"] != "pass": raise ValueError("QA 未通过，不能导入或批准")
                from .importer import import_drafts
                result = import_drafts(memory, [job], [candidate], glossary)
                if result.issues or result.conflicts: raise ValueError(json.dumps({"issues": result.issues, "conflicts": result.conflicts}, ensure_ascii=False))
                if action == "approve":
                    record = next(r for r in memory.records if r.source_key == job.source_key and r.status == "draft")
                    approval_issues = approve(memory, record.record_id, self._segment(job), reviewer=reviewer, glossary=glossary)
                    if any(x.severity == "error" for x in approval_issues): raise ValueError("批准失败: " + "; ".join(x.message for x in approval_issues))
                memory.save(self.memory_path)
            self._save_candidates(candidates)
            return {"message": "已保存" if action == "save" else ("已导入 draft" if action == "draft" else "已批准")}

    def _save_candidates(self, candidates: list[TranslationCandidate]) -> None:
        self.candidates_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.candidates_path.with_suffix(self.candidates_path.suffix + ".tmp")
        temporary.write_text(json.dumps(candidates_payload(candidates), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(self.candidates_path)


def serve(jobs: Path, candidates: Path, memory: Path, glossary: Path, host: str = "127.0.0.1", port: int = 8765) -> None:
    app = ReviewApp(jobs, candidates, memory, glossary)

    class Handler(BaseHTTPRequestHandler):
        def _json(self, value: Any, status: int = 200) -> None:
            raw = json.dumps(value, ensure_ascii=False).encode("utf-8")
            self.send_response(status); self.send_header("Content-Type", "application/json; charset=utf-8"); self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw)
        def do_GET(self) -> None:
            try:
                if urlparse(self.path).path == "/":
                    raw = HTML.encode("utf-8"); self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw)
                elif urlparse(self.path).path == "/api/state": self._json(app.state())
                else: self._json({"error": "Not found"}, 404)
            except Exception as exc: self._json({"error": str(exc)}, 500)
        def do_POST(self) -> None:
            try:
                path = urlparse(self.path).path; length = int(self.headers.get("Content-Length", "0")); body = json.loads(self.rfile.read(length) or b"{}")
                if path.startswith("/api/item/"):
                    self._json(app.update(path.rsplit("/", 1)[1], str(body.get("target", "")), str(body.get("action", "save")), str(body.get("reviewer", "local-ui"))))
                elif path == "/api/terms": self._json(app.add_term(str(body.get("source", "")), str(body.get("target", ""))))
                else: self._json({"error": "Not found"}, 404)
            except Exception as exc: self._json({"error": str(exc)}, 400)
        def log_message(self, *_: Any) -> None: pass

    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Review UI: http://{host}:{port}")
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
