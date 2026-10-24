import {fractionValues} from './engine.mjs';
export const initialVisuals=()=>({hero:{n:1},whole:{size:20},fraction:{n:1,den:4},equal:{factor:2},decimal:{n:25},percent:{n:25},connect:{n:25}});
const frac=(n,d)=>`<span class="fraction" aria-label="${n}/${d}"><span>${n}</span><span>${d}</span></span>`;
const eq='<span class="equals">=</span>';
const shell=(label,body)=>`<svg class="figure-svg" viewBox="0 0 440 190" role="img" aria-label="${label}">${body}</svg>`;
function bar(n,d,y=40,width=360){return `<rect class="base" x="40" y="${y}" width="${width}" height="42" rx="3"/><rect class="fill" x="40" y="${y}" width="${width*n/d}" height="42" rx="3"/>`+Array.from({length:d-1},(_,i)=>`<path class="divide" d="M${40+(i+1)*width/d} ${y}v42"/>`).join('');}
const segments=(key,values,selected,labels=values)=>`<div class="segmented">${values.map((v,i)=>`<button type="button" data-visual-key="${key}" data-visual-value="${v}" aria-pressed="${v===selected}">${labels[i]}</button>`).join('')}</div>`;
const range=(key,label,n,max)=>`<label class="figure-control"><span>${label}</span><input type="range" min="${key==='factor'?1:0}" max="${max}" step="1" value="${n}" data-range-key="${key}" aria-label="${label}"><output data-range-output>${n}</output></label>`;
export function figureData(type,v){
  let svg,equation,caption,controls;
  if(type==='hero'){
    const a=v.n*Math.PI/2,x=220+76*Math.sin(a),y=91-76*Math.cos(a);
    svg=shell(`同一个圆的 ${v.n}/4 涂色`,`<circle class="base" cx="220" cy="91" r="76"/><path class="fill" d="M220 91L220 15A76 76 0 ${v.n>2?1:0} 1 ${x} ${y}Z"/><path class="divide" d="M220 15v152M144 91h152"/>`);
    const values=fractionValues(v.n,4);equation=`${frac(v.n===2?1:v.n,v.n===2?2:4)}${eq}<span>${values.decimal}</span>${eq}<span>${values.percent}</span>`;
    caption='点一点，看看三种写法怎样一起变化。';controls=segments('n',[1,2,3],v.n,['1/4','1/2','3/4']);
  }else if(type==='whole'){
    const left=v.size,right=40;
    svg=shell(`第一条纸带长 ${left} 厘米，涂色一半长 ${left/2} 厘米；第二条长 40 厘米，涂色一半长 20 厘米`,`<text x="40" y="24">整体 ${left} 厘米</text>${bar(1,2,35,left*7)}<text x="40" y="115">整体 40 厘米</text>${bar(1,2,126,280)}`);
    equation=`<span>${left/2} 厘米</span><span class="equals">${left===right?'=':'<'}</span><span>20 厘米</span>`;
    caption=`各取一半：${left} ÷ 2 = ${left/2}，40 ÷ 2 = 20。${left===right?'整体相同，这两份一样长。':'整体不同，这两份不一样长。'}`;
    controls=segments('size',[20,40],v.size,['第一条 20 厘米','第一条 40 厘米']);
  }else if(type==='fraction'){
    svg=shell(`平均分成 ${v.den} 份，涂色 ${v.n} 份`,bar(v.n,v.den,68));equation=frac(v.n,v.den);
    caption=`总共 ${v.den} 份，涂色 ${v.n} 份。每一份一样大。`;
    controls=segments('den',[4,8],v.den,['平均分 4 份','平均分 8 份'])+range('n','涂色份数',v.n,v.den);
  }else if(type==='equal'){
    svg=shell(`同样大的两条纸带，上面涂色二分之一，下面涂色 ${v.factor}/${v.factor*2}，两处一样大`,bar(1,2,30)+bar(v.factor,v.factor*2,120));
    equation=`${frac(1,2)}${eq}${frac(v.factor,v.factor*2)}`;caption=`分子和分母都乘 ${v.factor}，涂色部分占整体的比例不变。`;
    controls=range('factor','每份再分几份',v.factor,4);
  }else if(type==='decimal'||type==='percent'){
    const shapes=Array.from({length:100},(_,i)=>type==='percent'?`<circle cx="${128+(i%10)*20}" cy="${10+Math.floor(i/10)*18}" r="5.5" class="${i<v.n?'fill':'base'}"/>`:`<rect x="${128+(i%10)*19}" y="${1+Math.floor(i/10)*18}" width="16" height="15" rx="1" class="${i<v.n?'fill':'base'}"/>`).join('');
    svg=shell(`一百个${type==='percent'?'圆点':'等大的方格'}中有 ${v.n} 个涂色`,shapes);
    equation=type==='percent'?`<span>${v.n}%</span>${eq}${frac(v.n,100)}${eq}<span>${v.n/100}</span>`:`${frac(v.n,100)}${eq}<span>${v.n/100}</span>`;
    caption=type==='percent'?`100 份中的 ${v.n} 份，占整体的 ${v.n}%。`:`${v.n} 个百分之一，写成小数是 ${v.n/100}。`;
    controls=range('n','涂色数量',v.n,100);
  }else{
    const x=40+360*v.n/100;
    svg=shell(`0 到 1 的数轴，标出 ${v.n/100} 的位置`,`<path class="stroke" d="M40 104h360"/>`+Array.from({length:5},(_,i)=>`<path class="stroke" d="M${40+i*90} 98v12"/><text x="${40+i*90}" y="139" text-anchor="middle">${i/4}</text>`).join('')+`<path d="M${x} 44v53" stroke="#85a77b" stroke-width="2"/><circle cx="${x}" cy="104" r="7" class="fill"/><text x="${x}" y="30" text-anchor="middle">${v.n/100}</text>`);
    const divisors={20:[1,5],25:[1,4],50:[1,2],75:[3,4]},[n,d]=divisors[v.n];
    equation=`${frac(n,d)}${eq}<span>${v.n/100}</span>${eq}<span>${v.n}%</span>`;
    caption='三种表达，在数轴上落在同一个位置。';controls=segments('n',[20,25,50,75],v.n,['0.2','0.25','0.5','0.75']);
  }
  return {svg,equation,caption,controls};
}
export function renderFigure(type,v){const d=figureData(type,v);return `<div class="math-visual" data-figure="${type}"><div class="visual-board"><div class="figure-drawing">${d.svg}</div><div class="equation">${d.equation}</div></div><div class="figure-controls">${d.controls}</div><p class="figure-caption" aria-live="polite">${d.caption}</p></div>`;}
