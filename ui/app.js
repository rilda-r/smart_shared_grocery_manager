const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
const calm=matchMedia('(prefers-reduced-motion:reduce)').matches;
/* Phase 1: zoom through the wordmark, parallax fragments */
function scene(){
 const t=$('#track'),max=t.offsetHeight-innerHeight,p=Math.min(1,Math.max(0,scrollY/max));
 if(!calm){
  $('#mark').style.transform=`scale(${1+Math.pow(p,2.2)*45})`;
  $('#mark').style.opacity=p>.8?Math.max(0,1-(p-.8)*5):1;
  $$('.shape,.frag').forEach(el=>el.style.transform=`translateY(${-scrollY*el.dataset.v*.4}px)`);
 }
 $('#hint').style.opacity=1-p*6;
}
addEventListener('scroll',()=>requestAnimationFrame(scene),{passive:true});scene();
/* Phase 2: auth tabs */
$$('.tabs button').forEach(b=>b.onclick=()=>{
 $$('.tabs button').forEach(x=>x.classList.toggle('on',x===b));
 const up=b.dataset.t==='up';$('#hname').hidden=!up;
 $('#ftitle').textContent=up?'Set up your household':'Welcome back';$('#login').textContent=up?'Create account':'Login';
});
$('#login').onclick=()=>{
 $('#landing').classList.add('out');
 setTimeout(()=>{$('#landing').hidden=true;$('#app').hidden=false;scrollTo(0,0);
  requestAnimationFrame(()=>$('#app').classList.add('in'));},calm?0:500);
};
/* Phase 3: dashboard */
const BUDGET=2000;let spent=0;
const items=[{n:'Milk, 2 L',who:'Asha',p:120},{n:'Rice, 5 kg',who:'Ravi',p:340},{n:'Tomatoes, 1 kg',who:'Meera',p:60},{n:'Dish soap',who:'Dev',p:95}];
const fmt=n=>'₹ '+Math.round(n).toLocaleString('en-IN');
function countTo(el,from,to,fmtFn=fmt,ms=800){
 if(calm){el.textContent=fmtFn(to);return}
 const t0=performance.now();(function f(t){const k=Math.min(1,(t-t0)/ms);el.textContent=fmtFn(from+(to-from)*(1-Math.pow(1-k,3)));if(k<1)requestAnimationFrame(f)})(t0);
}
function renderBasket(){
 $('#basket').innerHTML=items.map((it,i)=>`<li><input type="checkbox" data-i="${i}" aria-label="Mark ${it.n} bought"><span>${it.n}</span><span class="tag">${it.who}</span><small>${fmt(it.p)}</small></li>`).join('');
 $$('#basket input').forEach(cb=>cb.onchange=()=>buy(cb));
}
function buy(cb){
 const it=items[cb.dataset.i],li=cb.closest('li');cb.disabled=true;
 const from=spent;spent+=it.p;
 countTo($('#spent'),from,spent);countTo($('#w3'),96+from,96+spent);
 $('#fill').style.width=Math.min(100,spent/BUDGET*100)+'%';$('#fill').classList.toggle('over',spent>BUDGET*.9);
 setTimeout(()=>{ /* lock after the count-up finishes */
  li.classList.add('lk');li.innerHTML=`<span>${it.n}</span><small>${it.who} · ${fmt(it.p)}</small><span class="lock" title="Locked">🔒</span>`;
  $('#ledger').appendChild(li);
 },calm?0:850);
}
renderBasket();$('#spent').textContent=fmt(0);
/* duplicate quantity */
let q=1;const setQ=d=>{q=Math.max(1,q+d);$('#q').textContent=q};
$('#plus').onclick=e=>{e.stopPropagation();setQ(1)};$('#minus').onclick=e=>{e.stopPropagation();setQ(-1)};
/* card clicks refresh analytics */
const info={basket:['Basket metrics',()=>`${$$('#basket li').length} items open · est. ${fmt(items.reduce((a,b)=>a+b.p,0))}`],dup:['Duplicate check',()=>`Milk requested twice this week. Merging saves ${fmt(120)}.`],ledger:['Ledger metrics',()=>`${$$('#ledger li').length} locked purchases · ${fmt(spent+96)} logged`]};
$$('.card').forEach(c=>c.onclick=()=>{
 $$('.card').forEach(x=>x.classList.toggle('sel',x===c));
 const [t,f]=info[c.dataset.k];$('#itl').textContent=t;$('#ihint').textContent=f();
 const to=spent+(c.dataset.k==='ledger'?96:0);countTo($('#spent'),parseFloat($('#spent').textContent.replace(/\D/g,''))||0,to,fmt,500);
});
/* invite QR (decorative pattern) */
$('#qr').innerHTML=Array.from({length:81},(_,i)=>{const r=i/9|0,c=i%9,f=(r<3&&c<3)||(r<3&&c>5)||(r>5&&c<3);return `<i class="${f||Math.sin(i*12.9898)>.1?'':'x'}"></i>`}).join('');
