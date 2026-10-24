export const VERSION='planet-2026-10-23.1';
export const SUBJECTS={math:'数学',chinese:'语文',english:'英语',science:'科学',physics:'物理',chemistry:'化学',biology:'生物',history:'历史',geography:'地理',morality_law:'道德与法治',info_tech:'信息科技',art:'艺术',pe_health:'体育与健康',labor:'劳动'};
export const COLORS={math:'#90b5eb',science:'#9bceb8',chinese:'#d8ba88',english:'#d4969b',physics:'#a0c8c5',chemistry:'#a8a4d4',biology:'#9fc48d',history:'#cda882',geography:'#90b8cc',morality_law:'#c2afc8',info_tech:'#9aaee0',art:'#d1a9ba',pe_health:'#a7c4b1',labor:'#b5bc92'};
export const TOPICS=[
 {id:'shadow',number:'01',title:'为什么影子会变长？',short:'光与影子',subject:'science',tag:'科学 × 测量',intro:'同一根小木杆，影子怎么一会儿长，一会儿短？',invitation:'移动光源，看看影子会发生什么。',concepts:['SC_S2_MS_05','M_G1_GM_07','M_G2_GM_12'],defaultModel:{angle:45,height:1},
  prediction:'你觉得什么会改变影子的长度？',guesses:['光源的位置','木杆的高度','这两种变化都有可能'],
  task:'先保持木杆不变，比较光源在高处和低处时的影子。再试试改变木杆的高度。',
  explain:'你发现光源的位置、木杆高度和影子长度之间有什么关系？',placeholder:'我把光源……，发现影子……。保持光源不变时……',
  takeaway:'在这个模型里，木杆高度相同时，光线越贴近地面，影子越长。光线方向相同时，更高的木杆会留下更长的影子。',
  condition:'简化模型：平坦地面、竖直木杆、方向相同的平行光线。光源位置表示光线方向，不是某个地点的真实时间。',
  hints:['固定木杆高度，把光线角度从 30° 调到 60°，各记下一次影长。','再固定光线角度，只改变木杆高度。一次只改变一个条件，更容易比较。'],
  challenge:{prompt:'木杆高度不变。光线与地面的角度从 60° 变为 30°，影子会怎样？',choices:['变长','变短','保持一样长'],answer:0,explanation:'光线变得更贴近地面，影子变长。可以回到实验里比较 60° 和 30°。'},
  next:['同一时刻，高楼的影子会比小树长吗？','怎样用影子比较两个物体的高度？'],
  sources:[{id:'nasa-shadow',title:'NASA · 光源位置与影子',url:'https://pwg.gsfc.nasa.gov/stargaze/Ssky.htm',supports:'太阳接近地平线时，竖直物体的影子较长。'}],
  relations:[['光的传播','光沿直线传播，木杆挡住一部分光。'],['长度测量','比较影子，需要记录长度和实验条件。'],['面积概念','影子的长度与影子覆盖的面积是不同的量。']]},
 {id:'halves',number:'02',title:'两个「一半」一样多吗？',short:'整体与一半',subject:'math',tag:'数学 × 比较',intro:'两条纸带都涂了一半，涂色的地方就一定一样长吗？',invitation:'改变纸带的整体长度，再比较涂色部分。',concepts:['M_G3_NS_01','M_G3_NS_02','M_G1_GM_07'],defaultModel:{whole:20,parts:2,taken:1},
  prediction:'两条纸带都取一半，你觉得哪种说法更准确？',guesses:['只要是一半，就一样长','还要看看整条纸带有多长','我想动手比较一下'],
  task:'右边纸带始终长 40 厘米。改变左边纸带的长度，再改变它的分法，比较两块涂色部分。',
  explain:'什么时候两个一半一样长？比较分数时，为什么要先看整体？',placeholder:'我比较了……。当两条纸带的整体……时，它们的一半……',
  takeaway:'分数说的是一部分占整体多少。同样是二分之一，整体长度不同，取出的一半也可能不同。比较实际长度，要同时看整体和所取的比例。',
  condition:'每条纸带都平均分。厘米表示实际长度；分数表示涂色部分占本条纸带的比例。右边固定为 40 厘米的二分之一。',
  hints:['先都取二分之一，把左边整体从 20 厘米改为 40 厘米，比较两次结果。','把 40 厘米平均分成 4 份，涂 2 份。它和 40 厘米的一半一样长吗？'],
  challenge:{prompt:'一条纸带长 60 厘米，另一条长 40 厘米，各取一半。两块涂色部分怎样比较？',choices:['一样长，都是一半','第一块长 10 厘米','第二块长 10 厘米'],answer:1,explanation:'60 的一半是 30，40 的一半是 20，第一块长 10 厘米。分数相同，整体也要一起看。'},
  next:['四分之二为什么等于二分之一？','不同的分数，也可能取出一样长的纸带吗？'],
  sources:[{id:'openstax-fraction',title:'OpenStax · 整体与分数图示',url:'https://openstax.org/books/prealgebra-2e/pages/4-1-visualize-fractions',supports:'分数以平均分的整体为基础，描述部分与整体的关系。'}],
  relations:[['分数意义','一半表示整体平均分成两份中的一份。'],['分数基本性质','同一整体的二分之一和四分之二表示相同部分。'],['长度单位','实际长度还要用厘米等单位描述。']]},
 {id:'scale',number:'03',title:'边长翻倍，面积也翻倍？',short:'放大与面积',subject:'math',tag:'数学 × 图形',intro:'把一张长方形照片的长和宽都放大两倍，需要的纸也只有两倍吗？',invitation:'拖动放大倍数，数一数它占了多少格。',concepts:['M_G2_GM_13','M_G2_GM_14','M_G3_NS_12'],defaultModel:{factor:2,width:3,height:2},
  prediction:'长和宽都变成原来的两倍，面积会变成几倍？',guesses:['2 倍','4 倍','我想数一数'],
  task:'先数原图形的格子。把长和宽一起放大，比较 1 倍、2 倍和 3 倍时的面积。',
  explain:'为什么长和宽都放大两倍，面积会变成四倍？',placeholder:'原来有……格。放大后每行……，共有……行，所以……',
  takeaway:'长和宽都放大 k 倍，行数和每行的格数都变成 k 倍，面积变成 k × k 倍。长度的变化与面积的变化要分别比较。',
  condition:'长方形保持形状，长和宽按相同比例放大；每个小方格为 1 平方厘米。只改变一条边时，结果不同。',
  hints:['放大到 2 倍后，用原来的长方形铺一铺：一行能放 2 个，一共能放 2 行。','试试 3 倍：每行和行数怎样一起变化？'],
  challenge:{prompt:'一张长方形的长和宽都变成原来的 3 倍，它的面积会变成几倍？',choices:['3 倍','6 倍','9 倍'],answer:2,explanation:'长变为 3 倍，宽也变为 3 倍，面积变为 3 × 3 = 9 倍。'},
  next:['如果只把长放大两倍，面积会怎样？','体积的变化也能这样数出来吗？'],
  sources:[{id:'openstax-area',title:'OpenStax · 长方形与面积',url:'https://openstax.org/books/prealgebra-2e/pages/9-4-use-properties-of-rectangles-triangles-and-trapezoids',supports:'长方形面积等于长乘宽，单位为平方单位。'}],
  relations:[['长方形面积','用行数乘每行格数求出面积。'],['面积单位','每个单位格覆盖相同面积，便于比较。'],['比例','两条边按相同倍数变化，观察面积的变化。']]}
];
export const BY_ID=new Map(TOPICS.map(t=>[t.id,t]));
export const topicForConcept=id=>TOPICS.filter(t=>t.concepts.includes(id));
// Unreviewed raw edges never become a child's recommended learning relations.
export function conceptContext(graph,id){
 if(!graph?.nodes)return null;const index=new Map(graph.nodes.map(n=>[n.id,n])),node=index.get(id);if(!node)return null;
 const topics=topicForConcept(id),links=new Map();for(const t of topics)t.concepts.forEach((nid,i)=>{if(nid!==id&&index.has(nid))links.set(nid,{node:index.get(nid),reason:t.relations[i][1]});});
 const curated=links.size>0,neighbours=curated?[...links.values()]:graph.nodes.filter(n=>n.id!==id&&n.subject===node.subject&&n.domain===node.domain&&n.subdomain===node.subdomain).slice(0,5).map(n=>({node:n,reason:''}));
 return {node,topics,curated,neighbours};
}

// Match everyday Chinese wording and the actual concepts taught by a topic.
export function searchCatalog(graph,query){const normalize=value=>String(value||'').normalize('NFKC').toLowerCase().replace(/[\p{P}\p{Z}\s]/gu,'').replace(/的/g,'');const key=normalize(query),nodes=graph?.nodes||[],byId=new Map(nodes.map(n=>[n.id,n]));return {topics:TOPICS.filter(t=>!key||normalize([t.title,t.short,t.tag,t.invitation,...t.concepts.map(id=>byId.get(id)?.title||'')].join(' ')).includes(key)),matches:key?nodes.filter(n=>normalize(`${n.title} ${n.domain||''} ${SUBJECTS[n.subject]||''}`).includes(key)).slice(0,12):[]};}
