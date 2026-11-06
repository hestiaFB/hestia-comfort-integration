import type {Connection, Unsubscribe} from './types';
/** One subscription per room and per page, whatever the number of cards showing it (PLAN-OPTIMISATION.md, point 13): the
 *  Labo's Confort tab opened 45 subscriptions for 28 cards, each one sent, converted and read again. The cards of a room
 *  share it; a card added later gets the last message at once; the last card gone closes it. */
type Shared={listeners:Set<(event:unknown)=>void>;last?:unknown;ready:Promise<Unsubscribe>;closed:boolean};
const pages=new WeakMap<Connection,Map<string,Shared>>();

export function subscribeShared(connection:Connection,message:Record<string,unknown>,listener:(event:unknown)=>void):Promise<Unsubscribe> {
  let byMessage=pages.get(connection);
  if(!byMessage){byMessage=new Map();pages.set(connection,byMessage);}
  const key=JSON.stringify(message),table=byMessage;
  let shared=table.get(key);
  if(!shared){
    const created:Shared={listeners:new Set(),closed:false,ready:undefined as unknown as Promise<Unsubscribe>};
    created.ready=connection.subscribeMessage<unknown>(event=>{created.last=event;for(const l of [...created.listeners])l(event);},message);
    // A subscription refused or lost is asked again by the next card, never kept broken.
    created.ready.catch(()=>{created.closed=true;if(table.get(key)===created)table.delete(key);});
    table.set(key,created);shared=created;
  }
  const found=shared;
  // A message seen directly is not given again from `last`.
  let seen=false;
  const own=(event:unknown)=>{seen=true;listener(event);};
  found.listeners.add(own);
  return found.ready.then(()=>{
    if(found.last!==undefined)queueMicrotask(()=>{if(!seen&&found.listeners.has(own))own(found.last);});
    return async()=>{
      found.listeners.delete(own);
      if(found.listeners.size||found.closed)return;
      found.closed=true;
      if(table.get(key)===found)table.delete(key);
      const remove=await found.ready;await remove();
    };
  },error=>{found.listeners.delete(own);throw error;});
}
