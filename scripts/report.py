"""Publish transparent domain coverage, errors and provenance; no ZIP output."""
from pathlib import Path
from datetime import datetime,timezone
import json,html,hashlib
root=Path(__file__).resolve().parents[1]
r=json.loads((root/'data/validation.json').read_text());e=json.loads((root/'data/eop.json').read_text());a=json.loads((root/'data/error-investigation.json').read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
p={'model':r['model'],'scope':r['scope'],'domain':r['domain'],'ephemeris':{'name':'DE441','url':'https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de441_part-2.bsp','sha256':sha(root/'data/de441-solar.bsp'),'segments':'0→3,0→10,3→399; original Type2 coefficients,1972–2100subset'},'jpl_eop':{k:v for k,v in e['jpl'].items() if k!='rows'},'iers_eop':{k:e[k] for k in ['source','url','retrieved','sha256']},'erfa':{'source':'https://github.com/THRASTRO/sofa.js','sha256':sha(root/'vendor/erfa.min.js'),'license':'vendor/LICENSE-ERFA-JS.txt'},'runtime_privacy':'All arithmetic local; no geolocation/storage/coordinate transmission/calculation APIs','validation':{'horizons_cases':r['horizons']['cases'],'native_cases':r['native']['cases'],'boundary_checks':r['boundaries'],'spk_boundaries':r.get('spk_boundaries')},'unresolved':'Exact Horizons legacy EOP ASCII unavailable in this investigation; remaining submillisecond terms not fully isolated; no empirical correction applied.'}
(root/'data/provenance.json').write_text(json.dumps(p,ensure_ascii=False,indent=2))
names={'all':'全体样本（含近极点、未来外推）','nonpolar':'|纬度| ≤ 85°','observed_nonpolar':'|纬度| ≤ 85°，观测数据区','predicted_nonpolar':'|纬度| ≤ 85°，预测数据区','extrapolated_nonpolar':'|纬度| ≤ 85°，固定末值外推','polar':'|纬度| > 85°','holdout':'随机保留地点'}
rows=''
for k,label in names.items():
 s=r['horizons'][k];rows+='<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in [label,s['count'],f"{s['max_abs_ms']/1000:.9f}",f"{s['p95_ms']/1000:.9f}",f"{s['p99_ms']/1000:.9f}",f"{s['rms_ms']/1000:.9f}"])+'</tr>'
worst=r['horizons']['all']['worst'];when=datetime.fromtimestamp(worst['ms']/1000,timezone.utc).isoformat()
ab=a['confirmed_1973_site2_error_budget_ms'];abrows=''.join(f'<tr><td>{label}</td><td>{ab[key]:+.6f}</td></tr>' for key,label in [('IERS','原 IERS 输入'),('JPL_DUT1_only','只换 JPL DUT1'),('JPL_DUT1_and_pole','再换 JPL 极移'),('all_JPL_EOP2','再换 JPL dX/dY')])
body=f'''<a href="index.html">返回计算器</a><h1>全定义域分层测试与误差调查</h1><p class="lead">{r['horizons']['cases']:,} 组 Horizons 对照 · {r['native']['cases']:,} 组原生库校验 · {r['boundaries']['checks']} 项边界检查</p>
<div class="notice"><strong>没有把近极点的差异隐藏在几毫秒的结论里。</strong><p>全体样本最大差异 {r['horizons']['all']['max_abs_ms']/1000:.3f} 秒；|纬度|≤85° 的样本最大差异 {r['horizons']['nonpolar']['max_abs_ms']:.3f} 毫秒。有限采样不能证明连续定义域上的全局误差上界。当前实现采用现代参考框架，未承诺逐位复刻 Horizons。</p></div>
<h2>实际覆盖了什么</h2><p>Horizons：40个地点×1,055个时刻。地点包括等面积分布、赤道、±180°、南北85°/89°/89.99°/89.999999°和12个随机保留地点；高度覆盖−1000至100000米。日期包含1973–2027逐月分层、1972及2028–2099扩展点、全部数据内闰秒邻域和固定种子随机时刻。观测、预测与固定末值外推分别统计。</p>
<p>原生校验：每日20,044点、SPK分段邻域58,440点、随机保留32,768点、输入角点224点、人工EOP压力2,048点。浏览器模型与独立的原生ERFA+jplephem实现最大差异 {r['native']['max_abs_ms']*1000:.6f} 微秒。这是实现一致性检查，不等于物理精度认证。</p>
<p>另有 {r.get('spk_boundaries',{}).get('cases','待生成')} 个原始SPK记录边界及其前后1微秒位置/速度对照。检查了{r['boundaries']['leap_events']}个闰秒事件、输入范围、±180°物理等价性、未来外推必须显式启用等条件。</p>
<h2>Horizons 对照分布</h2><p>表中所有误差单位均为<strong>秒</strong>。日期和地点使用完全相同的数值输入；两套参考框架不完全相同。P95/P99为绝对差异的分位数。</p><div class="scroll"><table><thead><tr><th>范围</th><th>样本数</th><th>最大绝对差</th><th>P95</th><th>P99</th><th>RMS</th></tr></thead><tbody>{rows}</tbody></table></div>
<p>全域最差样本：UTC {when}；经度 {worst['longitude']}°，纬度 {worst['latitude']}°，椭球高 {worst['height']} m。极点附近即使数值程序工作正常，参考子午面也会高度不稳定。</p>
<h2>原来的 3.689 毫秒来自哪里</h2><p>固定1973-01-02 00:00 UTC、135°E、35°N、100m，其余计算保持不变。逐项替换产生以下可复算的变化：</p><table><thead><tr><th>输入替换</th><th>本地−Horizons / 毫秒</th></tr></thead><tbody>{abrows}</tbody></table>
<p>这验证了UT1、极移、章动修正数据差异对该样本的贡献。新的默认源采用公开JPL EOP2，并保留IERS选项。</p>
<h2>为什么近极点可能相差很大</h2><p>Horizons采用ITRF93与修正的IAU1976/1980；公开JPL EOP2采用ITRF2008/ICRF2与IAU2006/2000A。微小框架/极移变化对经度的影响近似随 tan(纬度) 放大。当纬度为89.999999°，离极点仅3.6毫角秒，而参考框架方向差异可达同等量级，线性近似也会失效。数值相同的经纬度在不同框架下不再代表完全相同的子午面。页面对 |纬度|>85° 显式提示，不宣称全域毫秒精度。</p>
<h2>尚未完全解决的部分</h2><p>JPL旧版EOP ASCII的官方端点本次未能获取，因此剩余子毫秒项无法全部分别归因到旧版插值、参考原点和潮汐修正。已用官方ITRF变换、NAIF Earth PCK做诊断，但部分变换或混合模型并不等于完整复现，没有为了减小样本误差而加入经验偏移。未来固定EOP外推也不是未来真实地球自转的可靠预报。</p>
<h2>输入边界和复现</h2><p>经度[-180°,180°]、纬度(-90°,90°)、椭球高[-1000,100000]m。东九区时间1972-01-01 09:15至2099-12-31 23:59:59.999；自动模式还须满足所选EOP覆盖范围。角分为整数0–59，角秒为[0,60)内小数。闰秒标签23:59:60不被日期控件接受，但前后跳变已验证。</p>
<pre>node tests/full-domain.cjs\nnode tests/spk-boundaries.cjs\npython3 scripts/report.py</pre><p>重放测试不调用API。原生参考生成器、人工坐标计划、缓存参考值和分项调查随源码保存。</p>
<p><a href="data/validation.json">完整统计 JSON</a> · <a href="data/provenance.json">来源与哈希</a> · <a href="data/error-investigation.json">调查记录</a> · <a href="https://ssd.jpl.nasa.gov/horizons/manual.html">Horizons 官方定义</a> · <a href="https://eop-external.jpl.nasa.gov/eop2/261118_190003-marge_eop2.long">JPL EOP2 冻结数据</a> · <a href="https://iers-conventions.obspm.fr/conventions/content/tn36.pdf">IERS 框架变换</a></p>'''
style='body{font-family:system-ui,sans-serif;max-width:1100px;margin:40px auto;padding:0 22px;color:#142b3a;line-height:1.8;background:#f7fafc}h1{font-size:30px}h2{margin-top:34px;font-size:21px}.lead{color:#526575}.notice{background:#fff1dc;border:1px solid #d8a65d;padding:20px;border-radius:12px}.notice p{margin-bottom:0}.scroll{overflow-x:auto}table{border-collapse:collapse;font-size:14px;width:100%;font-variant-numeric:tabular-nums;background:white}th,td{text-align:left;border-bottom:1px solid #d5e0e6;padding:10px;white-space:nowrap}th{background:#e8f0f5}a{color:#176681}pre{background:#e8f0f5;padding:16px;overflow:auto}'
(root/'validation.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>太阳时：全域测试与误差调查</title><style>'+style+'</style>'+body+'</html>')
print('Updated validation report and provenance')
