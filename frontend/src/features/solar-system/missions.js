// Historical launch archive, not live telemetry or reconstructed spacecraft paths.
export const MISSIONS = Object.freeze([
  { id: 'mariner-10', name: '水手 10 号', english: 'Mariner 10', launch: '1973-11-03', targets: ['venus', 'mercury'], kind: '飞掠探测', note: '借助金星引力改变航向，成为首个近距离探测水星的航天器。', source: 'https://science.nasa.gov/mission/mariner-10/' },
  { id: 'voyager-2', name: '旅行者 2 号', english: 'Voyager 2', launch: '1977-08-20', targets: ['jupiter', 'saturn', 'uranus', 'neptune'], kind: '飞掠探测', note: '依次飞掠四颗外侧巨行星，把近距离探索延伸到天王星与海王星。', source: 'https://science.nasa.gov/mission/voyager/voyager-2/' },
  { id: 'voyager-1', name: '旅行者 1 号', english: 'Voyager 1', launch: '1977-09-05', targets: ['jupiter', 'saturn'], kind: '飞掠探测', note: '从木星到土星，观察巨行星、行星环和卫星，再继续向外远行。', source: 'https://science.nasa.gov/mission/voyager/voyager-1/' },
  { id: 'magellan', name: '麦哲伦号', english: 'Magellan', launch: '1989-05-04', targets: ['venus'], kind: '轨道探测', note: '用雷达穿过金星厚重的云层，绘制其表面地形。', source: 'https://science.nasa.gov/mission/magellan/' },
  { id: 'mars-pathfinder', name: '火星探路者', english: 'Mars Pathfinder', launch: '1996-12-04', targets: ['mars'], kind: '着陆与巡视', note: '携带索杰纳巡视器着陆，验证在火星表面开展移动探测的技术。', source: 'https://science.nasa.gov/mission/mars-pathfinder/' },
  { id: 'cassini', name: '卡西尼—惠更斯', english: 'Cassini–Huygens', launch: '1997-10-15', targets: ['saturn'], kind: '轨道探测与着陆', note: 'NASA、ESA 与 ASI 合作探索土星系统；惠更斯探测器下降到土卫六表面。', source: 'https://science.nasa.gov/mission/cassini/the-journey/timeline/' },
  { id: 'messenger', name: '信使号', english: 'MESSENGER', launch: '2004-08-03', targets: ['mercury'], kind: '轨道探测', note: '首个环绕水星运行的探测器，研究其地质、组成和磁场。', source: 'https://www.nasa.gov/history/15-years-ago-messenger-launched-to-orbit-mercury/' },
  { id: 'juno', name: '朱诺号', english: 'Juno', launch: '2011-08-05', targets: ['jupiter'], kind: '轨道探测', note: '从极轨道观测木星的内部结构与磁场，追问这颗巨行星如何形成。', source: 'https://science.nasa.gov/mission/juno/' },
  { id: 'curiosity', name: '好奇号', english: 'Curiosity', launch: '2011-11-26', targets: ['mars'], kind: '着陆与巡视', note: '在盖尔撞击坑研究岩石与环境，寻找古代火星适合微生物生存的条件。', source: 'https://science.nasa.gov/mission/msl-curiosity/' },
  { id: 'perseverance', name: '毅力号', english: 'Perseverance', launch: '2020-07-30', targets: ['mars'], kind: '着陆与巡视', note: '探索杰泽罗撞击坑，研究古代环境并采集岩石样本；寻找生命迹象不等于已经发现生命。', source: 'https://science.nasa.gov/mission/mars-2020-perseverance/' },
].map(mission => Object.freeze({ ...mission, targets: Object.freeze(mission.targets) })))
export function filterMissions({ planet = '', era = '', query = '' } = {}) {
  const words = query.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean)
  return MISSIONS.filter(m => (!planet || m.targets.includes(planet)) && (!era || (era === 'classic' ? Number(m.launch.slice(0, 4)) < 2000 : Number(m.launch.slice(0, 4)) >= 2000)) && words.every(word => `${m.name} ${m.english} ${m.note} ${m.kind}`.toLocaleLowerCase().includes(word)))
}
