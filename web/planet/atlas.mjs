import {TOPICS,SUBJECTS} from './content.mjs';

// These short guides cover the part used in an existing experiment, not a full
// course for the graph node. They remain drafts pending education review.
const fraction=TOPICS.find(t=>t.id==='halves').sources[0];
const area=TOPICS.find(t=>t.id==='scale').sources[0];
const light=TOPICS.find(t=>t.id==='shadow').sources[0];
export const GUIDES={
 M_G3_NS_11:{idea:'比可以描述两个量之间的倍数关系。比较之前，需要说清楚这两个量是什么，并使用相同单位。',example:'同一光线下，木杆高1米、影长1米；旗杆影长6米。旗杆影长是木杆的6倍，因此高度也是6倍。',question:'如果木杆高2米，影长也是旗杆影长的六分之一，旗杆会高多少？',scope:'用于相同光线、竖直杆与水平地面的测高模型。',source:TOPICS.find(t=>t.id==='flagpole').sources[0]},
 M_G3_NS_13:{idea:'在条件保持不变时，一个量变成几倍，另一个量也相应变成几倍，可以从成对的数据中寻找这种关系。',example:'保持光线方向相同，高度从1米到2米，影长也变成原来的2倍。光线方向改变后，高度与影长的具体比例也会改变。',question:'为什么比较影长来测高，需要确认两边的光线相同？',scope:'本导读只讨论固定光线时高度与影长的关系，不覆盖正比例的完整课程。',source:TOPICS.find(t=>t.id==='flagpole').sources[0]},
 SC_S2_MS_05:{idea:'先只看光被挡住时的影子。木杆挡住一部分光，地面上便有一块没有被光直接照到的地方。',example:'在我们的平行光模型中，保持木杆高度不变，把光线从高处移向低处，影子会变长。',question:'固定光线角度，再把木杆变高，影子会怎样？',scope:'本次探索光与影子，不包含反射的完整内容。',source:light},
 M_G1_GM_07:{idea:'长度描述从一端到另一端有多远。比较两段长度，要先用同样的单位。',example:'1 米是 100 厘米。20 厘米和 0.2 米表示相同的长度。',question:'两条纸带都取一半，为什么还要知道整条纸带有多长？',scope:'在纸带和影子实验中使用米、厘米。',source:area},
 M_G2_GM_12:{idea:'面积描述一个平面图形覆盖了多大的地方。长度和面积回答的是不同的问题。',example:'3 厘米长、2 厘米宽的长方形，能铺下 6 个边长为 1 厘米的小正方形，面积是 6 平方厘米。',question:'只知道影子有多长，能知道它覆盖的面积吗？',scope:'从长方形和单位格理解面积。',source:area},
 M_G3_NS_01:{idea:'把一个整体平均分成几份，取其中的几份，就可以用分数表示。先要说清楚，谁是整体。',example:'20 厘米纸带的一半长 10 厘米；40 厘米纸带的一半长 20 厘米。都是二分之一，实际长度却不同。',question:'如果涂色部分一样长，它们占各自整体的分数一定相同吗？',scope:'以平均分的纸带比较部分与整体。',source:fraction},
 M_G3_NS_02:{idea:'同一个整体，换一种平均分法，也可能取出同样多的部分。',example:'同一条 40 厘米纸带，取 2 份中的 1 份是 20 厘米，取 4 份中的 2 份也是 20 厘米。所以二分之一等于四分之二。',question:'平均分成 8 份，要涂几份才能和一半一样长？',scope:'用同一整体理解等值分数，不改变整体后直接比较长度。',source:fraction},
 M_G2_GM_13:{idea:'长方形可以用同样大小的小正方形铺满。每行有几个、共有几行，相乘就得到总格数。',example:'长 3 厘米、宽 2 厘米，每格 1 平方厘米。每行 3 格，共 2 行，面积是 3 × 2 = 6 平方厘米。',question:'长和宽都变为原来的两倍，每行的格数和行数分别变成多少？',scope:'格子边长为 1 厘米，长与宽使用同样的长度单位。',source:area},
 M_G2_GM_14:{idea:'比较面积，要用同样大小的单位格。平方厘米是边长为 1 厘米的正方形的面积。',example:'1 平方米能铺下 100 × 100 个 1 平方厘米的小正方形，所以是 10,000 平方厘米。',question:'图形没变，只把单位格换得更小，数出的格数为什么会更多？',scope:'区分长度单位与面积单位。',source:area},
 M_G3_NS_12:{idea:'这里先比较图形放大前后的对应长度。长与宽都按相同倍数变化，图形的形状保持不变。',example:'原长方形是 3 × 2 厘米，变为 6 × 4 厘米。两条边都是原来的 2 倍，面积却从 6 变为 24 平方厘米，是原来的 4 倍。',question:'如果两条边都变成 3 倍，面积会变成几倍？',scope:'本次只探索等比放大，比例的其他内容暂未涵盖。',source:area}
};
export const guideFor=id=>Object.hasOwn(GUIDES,id)?GUIDES[id]:null;
export function subjectCatalog(graph,subject){
 const nodes=(graph?.nodes||[]).filter(n=>n.subject===subject),groups=new Map();
 for(const n of nodes){const key=n.domain||'其他';if(!groups.has(key))groups.set(key,[]);groups.get(key).push(n);}
 return {subject,title:SUBJECTS[subject],nodes,groups:[...groups].map(([title,nodes])=>({title,nodes})),topics:TOPICS.filter(t=>t.subject===subject)};
}
export function subjectIndex(graph){return Object.keys(SUBJECTS).map(s=>subjectCatalog(graph,s)).filter(s=>s.nodes.length);}

// All subject labels exist. Projected labels are hidden only by occlusion,
// viewport bounds, or a collision; the complete directory stays accessible.
export function placeLabels(candidates,width,height,active){
 const placed=[];for(const c of [...candidates].sort((a,b)=>(b.id===active)-(a.id===active)||b.front-a.front)){
  if(c.front<.14||c.x<c.width/2+8||c.x>width-c.width/2-8||c.y<24||c.y>height-24)continue;
  const box={...c,left:c.x-c.width/2-5,right:c.x+c.width/2+5,top:c.y-23,bottom:c.y+23};
  if(!placed.some(p=>box.left<p.right&&box.right>p.left&&box.top<p.bottom&&box.bottom>p.top))placed.push(box);
 }
 return new Set(placed.map(p=>p.id));
}
