#!/usr/bin/env node
// motion.js - motion-graphics Shorts (the "HeyGen look"), drawn as HTML and rendered frame by frame
// in the pre-installed Chromium. 1080x1920, 30 fps, no audio. batch.py adds voice and music.
//
//   node motion.js spec.timed.json out.mp4            full render
//   node motion.js spec.timed.json out.mp4 --stills D  stills at each scene's end, for QC
//
// Spec: "renderer": "motion" and scenes like
//   {"kind": "title", "kicker": "GTA 6 LAUNCH DAY", "text": ["3 QUESTIONS", "*3 ANSWERS*"], "sub": "..."}
//   {"kind": "item", "badge": "1", "label": "PRICE", "big": "UP TO *212 GB*",
//    "cards": [["STANDARD", "$79.99"], ["ULTIMATE", "$99.99", true]], "note": "Source: ..."}
//   {"kind": "cta", "text": ["STANDARD OR", "*ULTIMATE?*"], "sub": "Follow for more GTA 6 answers"}
// "brand": top-left channel name (default GTA STUFF GUY). "theme": neon (default) | sunset | ocean | ember | money | ink (Common Sense). Rotate themes so Shorts don't all look alike.
// *word* is highlighted. Scene durations come from batch.py (timed to the voice).
const fs = require('fs');
const { spawn } = require('child_process');
const { chromium } = require('playwright');

const W = 1080, H = 1920, FPS = 30;
const [specPath, outPath, flag, stillsDir] = process.argv.slice(2);
const spec = JSON.parse(fs.readFileSync(specPath, 'utf8'));
const font = (w) => fs.readFileSync(`/usr/share/fonts/truetype/google-fonts/Poppins-${w}.ttf`).toString('base64');

const THEMES = {
  neon:   {bg1: '#2a0f5c', bg2: '#140a35', bg3: '#07051a', b1: '#ff2e93', b2: '#19d3e0', b3: '#ffd23f', hl: '#ffd23f', kick: '#19d3e0', pop: '#ff2e93'},
  sunset: {bg1: '#7a1f2b', bg2: '#3a0d22', bg3: '#14040c', b1: '#ff7a1a', b2: '#ff2e6e', b3: '#ffe066', hl: '#ffe066', kick: '#ff9f1c', pop: '#ff2e6e'},
  ocean:  {bg1: '#063f5c', bg2: '#04263d', bg3: '#010f1a', b1: '#00e0c6', b2: '#2b7bff', b3: '#b6ff3b', hl: '#b6ff3b', kick: '#00e0c6', pop: '#2b7bff'},
  ember:  {bg1: '#3d0a0a', bg2: '#1c0606', bg3: '#070202', b1: '#ff3b1f', b2: '#ff9a1f', b3: '#ffd23f', hl: '#ffd23f', kick: '#ff9a1f', pop: '#ff3b1f'},
  ink:    {bg1: '#1f3d63', bg2: '#132840', bg3: '#08121f', b1: '#3ABFBF', b2: '#f4ecd8', b3: '#ffd23f', hl: '#ffd23f', kick: '#3ABFBF', pop: '#e4572e'},
  money:  {bg1: '#0b3d1e', bg2: '#06240f', bg3: '#020c05', b1: '#2bff88', b2: '#ffd23f', b3: '#19d3e0', hl: '#ffd23f', kick: '#2bff88', pop: '#16a34a'},
};
const T = THEMES[spec.theme] || THEMES.neon;
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;');
const hl = (s) => esc(s).replace(/\*(.+?)\*/g, '<span class="hl">$1</span>');

let starts = [], acc = 0;
for (const sc of spec.scenes) { starts.push(acc); acc += sc.dur; }
const TOTAL = acc;

function sceneHTML(sc, i) {
  let d = 0.05, parts = [];
  const add = (html, anim, step = 0.12) => { parts.push(html.replace('<div ', `<div data-a="${anim}" data-d="${d.toFixed(2)}" `)); d += step; };
  if (sc.kicker) add(`<div class="kicker">${esc(sc.kicker)}</div>`, 'left');
  if (sc.badge) add(`<div class="badge">${esc(sc.badge)}</div>`, 'spin', 0.18);
  if (sc.label) add(`<div class="label">${hl(sc.label)}</div>`, 'left');
  for (const t of sc.text || []) add(`<div class="head">${hl(t)}</div>`, 'pop', 0.16);
  if (sc.big) add(`<div class="big">${hl(sc.big)}</div>`, 'pop', 0.2);
  for (const c of sc.cards || []) add(`<div class="card${c[2] ? ' on' : ''}"><span>${esc(c[0])}</span><b>${esc(c[1])}</b></div>`, 'up', 0.16);
  if (sc.sub) add(`<div class="sub">${hl(sc.sub)}</div>`, 'fade');
  if (sc.note) add(`<div class="note">${esc(sc.note)}</div>`, 'fade');
  if (sc.kind === 'cta') add(`<div class="follow">FOLLOW</div>`, 'pulse');
  return `<section class="scene" data-s="${i}">${parts.join('')}</section>`;
}

const html = `<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{font-family:P;font-weight:700;src:url(data:font/ttf;base64,${font('Bold')})}
@font-face{font-family:P;font-weight:500;src:url(data:font/ttf;base64,${font('Medium')})}
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:${W}px;height:${H}px;overflow:hidden;background:#0b0820;font-family:P,sans-serif;color:#fff}
#bg{position:absolute;inset:0;background:radial-gradient(120% 80% at 50% 30%,${T.bg1} 0%,${T.bg2} 55%,${T.bg3} 100%)}
.blob{position:absolute;width:900px;height:900px;border-radius:50%;filter:blur(120px);opacity:.55}
#b1{background:${T.b1}}#b2{background:${T.b2}}#b3{background:${T.b3};opacity:.18;width:700px;height:700px}
#grid{position:absolute;inset:-200px;background-image:linear-gradient(rgba(255,255,255,.06) 2px,transparent 2px),linear-gradient(90deg,rgba(255,255,255,.06) 2px,transparent 2px);background-size:120px 120px;transform:perspective(900px) rotateX(55deg);transform-origin:50% 100%;top:900px}
#bar{position:absolute;left:0;top:0;height:14px;background:linear-gradient(90deg,${T.hl},${T.pop});box-shadow:0 0 30px ${T.pop}}
#brand{position:absolute;left:60px;top:150px;font-weight:700;font-size:34px;letter-spacing:6px;color:rgba(255,255,255,.7)}
#brand i{display:inline-block;width:18px;height:18px;border-radius:50%;background:${T.pop};margin-right:14px;box-shadow:0 0 18px ${T.pop};font-style:normal}
#wipe{position:absolute;top:-10%;height:120%;width:70%;background:linear-gradient(90deg,${T.pop},${T.hl});transform:skewX(-14deg);left:-90%}
.scene{position:absolute;left:0;right:0;top:260px;height:1140px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:26px;padding:0 70px;text-align:center;opacity:0}
.scene>div{will-change:transform,opacity}
.kicker{background:${T.kick};color:#07051a;font-weight:700;font-size:44px;letter-spacing:3px;padding:12px 34px;border-radius:60px}
.badge{width:190px;height:190px;border-radius:50%;background:${T.hl};color:#07051a;font-weight:700;font-size:130px;line-height:200px;box-shadow:0 0 0 14px rgba(255,210,63,.25),0 20px 60px rgba(0,0,0,.5)}
.label{font-weight:700;font-size:96px;letter-spacing:4px;text-shadow:0 8px 30px rgba(0,0,0,.6)}
.head{font-weight:700;font-size:150px;line-height:1.02;transform:skewX(-6deg);text-shadow:0 10px 40px rgba(0,0,0,.6)}
.big{font-weight:700;font-size:138px;line-height:1.05;transform:skewX(-6deg);text-shadow:0 10px 40px rgba(0,0,0,.6)}
.hl{color:${T.hl};text-shadow:0 0 40px rgba(255,210,63,.45),0 10px 40px rgba(0,0,0,.6)}
.card{width:880px;display:flex;justify-content:space-between;align-items:center;padding:30px 44px;border-radius:28px;background:rgba(255,255,255,.08);border:3px solid rgba(255,255,255,.18);font-size:52px}
.card span{font-weight:500;letter-spacing:2px}.card b{font-weight:700;font-size:70px}
.card.on{background:rgba(255,255,255,.12);border-color:${T.hl}}.card.on b{color:${T.hl}}
.sub{font-weight:500;font-size:58px;color:rgba(255,255,255,.9)}
.note{font-weight:500;font-size:38px;color:rgba(255,255,255,.6)}
.follow{background:${T.pop};font-weight:700;font-size:64px;letter-spacing:6px;padding:18px 70px;border-radius:80px;box-shadow:0 0 50px rgba(255,46,147,.7)}
</style></head><body>
<div id="bg"></div><div class="blob" id="b1"></div><div class="blob" id="b2"></div><div class="blob" id="b3"></div><div id="grid"></div>
<div id="brand"><i></i>${esc(spec.brand || "GTA STUFF GUY")}</div>
${spec.scenes.map(sceneHTML).join('\n')}
<div id="wipe"></div><div id="bar"></div>
<script>
const starts=${JSON.stringify(starts)}, durs=${JSON.stringify(spec.scenes.map(s => s.dur))}, TOTAL=${TOTAL};
const cl=(x)=>Math.max(0,Math.min(1,x));
const back=(x)=>{const c=1.7;return 1+(c+1)*Math.pow(x-1,3)+c*Math.pow(x-1,2)};
const out=(x)=>1-Math.pow(1-x,3);
const scenes=[...document.querySelectorAll('.scene')];
function render(t){
  const $=(id)=>document.getElementById(id);
  $('b1').style.transform='translate('+(-250+180*Math.sin(t*.35))+'px,'+(-150+140*Math.cos(t*.27))+'px)';
  $('b2').style.transform='translate('+(450+160*Math.cos(t*.31))+'px,'+(1000+150*Math.sin(t*.22))+'px)';
  $('b3').style.transform='translate('+(200+220*Math.sin(t*.19+1))+'px,'+(600+200*Math.cos(t*.23))+'px)';
  $('grid').style.backgroundPosition='0 '+(t*90%120)+'px';
  $('bar').style.width=(100*t/TOTAL)+'%';
  let wipe=-1;
  scenes.forEach((el,i)=>{
    const lt=t-starts[i], d=durs[i];
    const vis=lt>=0&&lt<d;
    el.style.opacity=vis?1:0;
    if(!vis)return;
    if(i>0&&lt<0.32)wipe=lt/0.32;
    const ex=i<scenes.length-1?cl((lt-(d-0.18))/0.18):0;
    el.querySelectorAll('[data-a]').forEach(e=>{
      const at=i===0?lt+1.5:lt;  // scene 1 is fully drawn at frame 0 (hook rule)
      const p=cl((at-parseFloat(e.dataset.d)-(i>0?0.12:0))/0.38), a=e.dataset.a;
      let tr='',op=out(p);
      if(a==='left')tr='translateX('+(-160*(1-out(p)))+'px)';
      else if(a==='up')tr='translateY('+(90*(1-out(p)))+'px)';
      else if(a==='pop')tr='scale('+(0.55+0.45*back(p))+')';
      else if(a==='spin')tr='scale('+back(p)+') rotate('+(-200*(1-out(p)))+'deg)';
      else if(a==='pulse')tr='scale('+(back(p)*(1+0.05*Math.sin(lt*6)))+')';
      const sk=e.classList.contains('head')||e.classList.contains('big')?' skewX(-6deg)':'';
      e.style.opacity=op*(1-ex);
      e.style.transform=tr+' translateY('+(-60*ex)+'px)'+sk;
    });
  });
  $('wipe').style.left=wipe<0?'-90%':(-90+200*out(wipe))+'%';
}
window.render=render;
</script></body></html>`;

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: W, height: H } });
  await page.setContent(html);
  await page.evaluate(() => document.fonts.ready);
  if (flag === '--stills') {
    fs.mkdirSync(stillsDir, { recursive: true });
    for (let i = 0; i < spec.scenes.length; i++) {
      for (const [tag, t] of [['mid', starts[i] + Math.min(0.6, spec.scenes[i].dur / 2)], ['end', starts[i] + spec.scenes[i].dur - 0.25]]) {
        await page.evaluate((t) => render(t), t);
        await page.screenshot({ path: `${stillsDir}/s${i + 1}_${tag}.png` });
      }
    }
    console.log('stills in', stillsDir);
    await browser.close();
    return;
  }
  const n = Math.round(TOTAL * FPS);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
    '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', outPath],
    { stdio: ['pipe', 'inherit', 'inherit'] });
  for (let k = 0; k < n; k++) {
    await page.evaluate((t) => render(t), k / FPS);
    const buf = await page.screenshot({ type: 'jpeg', quality: 92 });
    if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
  }
  ff.stdin.end();
  await new Promise((r, j) => ff.on('close', (c) => (c === 0 ? r() : j(new Error('ffmpeg ' + c)))));
  await browser.close();
  console.log(`wrote ${outPath} (${n} frames, ${TOTAL.toFixed(1)} s)`);
})().catch((e) => { console.error(e); process.exit(1); });
