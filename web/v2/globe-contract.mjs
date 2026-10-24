// Explicit bridge between the existing graph and the curated learning unit.
// Unknown concepts remain exploratory; they never acquire an invented lesson.
export const CONCEPT_LESSONS = Object.freeze({
  M_G3_NS_01:'fraction',
  M_G3_NS_02:'equal',
  M_G3_NS_09:'percent',
  M_G3_NS_10:'connect',
  M_G56_NS_01:'decimal'
});
export const lessonForConcept=id=>Object.hasOwn(CONCEPT_LESSONS,id)?CONCEPT_LESSONS[id]:null;
export function acceptedGlobeMessage(event,frameWindow,origin){
  if(!frameWindow||event.source!==frameWindow||event.origin!==origin)return null;
  const d=event.data;
  if(!d||typeof d!=='object'||Array.isArray(d))return null;
  if(d.type==='occ:globe-ready')return {type:'ready'};
  if(d.type==='occ:globe-state'&&typeof d.selected==='boolean')return {type:'state',selected:d.selected};
  if(d.type==='occ:globe-learn')return {type:'learn',route:lessonForConcept(d.conceptId)?`learn/${lessonForConcept(d.conceptId)}`:'topics'};
  return null;
}
