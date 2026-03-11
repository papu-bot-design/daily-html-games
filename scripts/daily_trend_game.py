import os, re, json, time, random
from datetime import datetime
import requests
from pytrends.request import TrendReq

ROOT = os.path.dirname(os.path.dirname(__file__))
GAMES_DIR = os.path.join(ROOT, 'games')
LIST_PATH = os.path.join(ROOT, 'games-list.md')
INDEX_PATH = os.path.join(ROOT, 'index.html')

headers = {'User-Agent': 'Mozilla/5.0'}

def slugify(s):
    s = re.sub(r'[^a-zA-Z0-9\s-]', '', s)
    s = re.sub(r'\s+', '-', s.strip()).lower()
    return s[:40] if s else 'trend-game'

def load_used():
    if not os.path.exists(LIST_PATH):
        return set()
    txt = open(LIST_PATH, 'r', encoding='utf-8').read().lower()
    return set(re.findall(r'—\s*([^\n]+)', txt))

def get_trends_pytrends():
    pytrends = TrendReq(hl='es-AR', tz=-180)
    topics = []
    for pn in ['argentina', 'united_states']:
        try:
            df = pytrends.trending_searches(pn=pn)
            topics += [str(x) for x in df[0].tolist()[:10]]
            time.sleep(2)
        except Exception:
            continue
    return topics

def get_trends_reddit():
    topics = []
    try:
        url = 'https://www.reddit.com/r/popular/hot.json?limit=20'
        data = requests.get(url, headers=headers, timeout=10).json()
        for child in data.get('data', {}).get('children', []):
            title = child.get('data', {}).get('title', '')
            if title:
                topics.append(title)
    except Exception:
        pass
    return topics

def pick_topic(trends, used):
    for t in trends:
        if t.lower() not in used:
            return t
    return random.choice(trends) if trends else 'Tendencia del día'

GAME_TEMPLATE = """<!doctype html>
<html lang=\"es\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no\" />
  <title>{title}</title>
  <style>
    html,body{{margin:0;padding:0;width:100%;height:100%;overflow:hidden;background:#0a0f1a;color:#fff;font-family:system-ui}}
    #hud{{position:fixed;top:10px;left:10px;z-index:2}}
    #overlay{{position:fixed;inset:0;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,.6);z-index:3;text-align:center}}
    .btn{{background:#1f5;color:#000;padding:10px 16px;border-radius:12px;font-weight:900;cursor:pointer;user-select:none}}
    canvas{{display:block;width:100%;height:100%}}
  </style>
</head>
<body>
  <div id=\"hud\">Score: <b id=\"score\">0</b> | Record: <b id=\"best\">0</b></div>
  <div id=\"overlay\"><div><div style=\"font-size:24px\"><b>{title}</b></div><div>Click/Tap para esquivar</div><div class=\"btn\" id=\"startBtn\">Iniciar</div></div></div>
  <canvas id=\"c\"></canvas>
  <script>
    const canvas = document.getElementById('c');
    const ctx = canvas.getContext('2d');
    const overlay = document.getElementById('overlay');
    const startBtn = document.getElementById('startBtn');
    const scoreEl = document.getElementById('score');
    const bestEl = document.getElementById('best');
    let W,H; function resize(){{W=canvas.width=innerWidth;H=canvas.height=innerHeight}} resize(); addEventListener('resize',resize);
    let running=false; let score=0; let best=+localStorage.getItem('{key}_best')||0;
    let player={{x:W/2,y:H-80,r:16}}; let obstacles=[]; let lastSpawn=0; let speed=2;
    function reset(){{score=0; speed=2; obstacles=[]; player.x=W/2;}}
    function spawn(){{ obstacles.push({{x:Math.random()*W,y:-20,r:10+Math.random()*10,vy:2+Math.random()*speed}}); }}
    function update(dt){{
      score += dt*10; speed += dt*0.15;
      lastSpawn += dt; if(lastSpawn>0.5){{spawn(); lastSpawn=0;}}
      obstacles.forEach(o=>o.y+=o.vy*60*dt);
      obstacles = obstacles.filter(o=>o.y<H+40);
      for(const o of obstacles){{ if(Math.hypot(player.x-o.x, player.y-o.y)<player.r+o.r){{ end(); return; }} }}
    }}
    function draw(){{
      ctx.fillStyle='#0a0f1a'; ctx.fillRect(0,0,W,H);
      ctx.fillStyle='#7ef'; ctx.beginPath(); ctx.arc(player.x,player.y,player.r,0,Math.PI*2); ctx.fill();
      ctx.fillStyle='#f55'; obstacles.forEach(o=>{{ctx.beginPath(); ctx.arc(o.x,o.y,o.r,0,Math.PI*2); ctx.fill();}});
      scoreEl.textContent = Math.floor(score); bestEl.textContent = best;
    }}
    function end(){{ running=false; if(score>best){{best=Math.floor(score); localStorage.setItem('{key}_best',best)}}
      overlay.style.display='flex'; overlay.innerHTML=`<div><div style=\"font-size:24px\"><b>Game Over</b></div><div>Score: ${{Math.floor(score)}}</div><div class='btn' id='restartBtn'>Reiniciar</div></div>`;
      document.getElementById('restartBtn').onclick=()=>{{overlay.style.display='none'; reset(); running=true;}};
    }}
    let last=performance.now(); function loop(t){{const dt=(t-last)/1000; last=t; if(running) update(dt); draw(); requestAnimationFrame(loop);}} requestAnimationFrame(loop);
    function move(x){{ player.x=Math.max(20,Math.min(W-20,x)); }}
    canvas.addEventListener('mousemove', e=>{{if(running) move(e.clientX)}});
    canvas.addEventListener('touchmove', e=>{{if(running) move(e.touches[0].clientX)}}, {{passive:true}});
    canvas.addEventListener('click', e=>{{ if(!running){{overlay.style.display='none'; reset(); running=true;}} else {{move(e.clientX);}} }});
    startBtn.onclick=()=>{{overlay.style.display='none'; reset(); running=true;}};
  </script>
</body>
</html>
"""

def main():
    used = load_used()
    trends = get_trends_pytrends() + get_trends_reddit()
    topic = pick_topic(trends, used)
    slug = slugify(topic)

    # determine next number
    existing = [d for d in os.listdir(GAMES_DIR) if d.startswith('juego-')]
    nums = [int(d.split('-')[1]) for d in existing if d.split('-')[1].isdigit()]
    next_num = max(nums) + 1 if nums else 1
    folder = f'juego-{next_num:03d}'
    game_path = os.path.join(GAMES_DIR, folder)
    os.makedirs(game_path, exist_ok=True)

    title = f"{topic[:40]}" if topic else "Tendencia del día"
    key = f"game_{next_num:03d}"
    html = GAME_TEMPLATE.format(title=title, key=key)
    with open(os.path.join(game_path, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(html)

    # update index.html
    index = open(INDEX_PATH, 'r', encoding='utf-8').read()
    card = f'''    <li class="card">\n      <div><b>Juego #{next_num:03d} — {title}</b></div>\n      <div>Juego inspirado en tendencia del día.</div>\n      <a href="games/{folder}/">Jugar</a>\n    </li>\n'''
    if card not in index:
        index = index.replace('</ul>', card + '</ul>')
        open(INDEX_PATH, 'w', encoding='utf-8').write(index)

    # update games-list.md
    lst = open(LIST_PATH, 'r', encoding='utf-8').read()
    insert = f"{next_num}. Juego #{next_num:03d} — {title} (publicado)\n"
    if insert not in lst:
        # insert after first line of list
        lst = lst.replace('1. Juego #001 — Meteoro Dodge (publicado)\n',
                          '1. Juego #001 — Meteoro Dodge (publicado)\n' + insert)
        open(LIST_PATH, 'w', encoding='utf-8').write(lst)

    summary = {
        'topic': topic,
        'folder': folder,
        'title': title,
        'timestamp': datetime.utcnow().isoformat()+'Z'
    }
    print(json.dumps(summary, ensure_ascii=False))

if __name__ == '__main__':
    main()
