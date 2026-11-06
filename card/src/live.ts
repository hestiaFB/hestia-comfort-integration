import {isView} from './view';
import {subscribeShared} from './shared';
import type {Connection, Unsubscribe, View} from './types';
/** Owns exactly one subscription. Late replies from previous rooms cannot leak. */
export class LiveView {
  private generation=0;
  private unsubscribe?:Unsubscribe;
  private retry?:ReturnType<typeof setTimeout>;
  private watchdog?:ReturnType<typeof setInterval>;
  private last=0;
  private connection?:Connection;
  private entry?:string;
  private running=false;
  private recovering=false;
  constructor(private onView:(v:View)=>void,private onProblem:(code:string)=>void,private onClear:()=>void){}
  start(connection:Connection,entry?:string) {
    if((this.running||this.recovering)&&this.connection===connection&&this.entry===entry) return;
    this.stop(); this.onClear(); this.connection=connection; this.entry=entry; this.running=true;
    void this.connect(this.generation);
    this.watchdog=setInterval(()=>{
      if(this.last&&Date.now()-this.last>75000){this.onClear();this.onProblem('stale');this.last=0;}
    },1000);
  }
  private async connect(generation:number) {
    try {
      // The page's one subscription to this room (shared.ts), whatever the number of its cards.
      const remove=await subscribeShared(this.connection!,{type:'hestia_comfort/subscribe',...(this.entry?{entry_id:this.entry}:{})},(event:unknown)=>{
        if(generation!==this.generation||!this.running) return;
        if(event && typeof event==='object' && 'reload' in event && event.reload===true){this.onClear();this.onProblem('reload');this.reconnect(generation);return;}
        if(event && typeof event==='object' && 'unavailable' in event && event.unavailable===true){this.onClear();this.onProblem('unavailable');return;}
        const view=event&&typeof event==='object'&&'view' in event?event.view:undefined;
        if(!isView(view) || (this.entry && view.entry_id!==this.entry)) {this.onClear();this.onProblem('version');return;}
        const age=Date.now()-Date.parse(view.computed_at);
        if(age>75000 || age< -60000){this.onClear();this.onProblem('stale');return;}
        this.last=Date.now();this.onView(view);
      });
      if(generation!==this.generation||!this.running) await remove(); else this.unsubscribe=remove;
    } catch(error) {
      if(generation!==this.generation||!this.running) return;
      this.onClear();this.onProblem((error as {code?:string})?.code??'connection');
      this.reconnect(generation);
    }
  }
  private reconnect(generation:number) {
    if(this.retry||generation!==this.generation) return;
    const connection=this.connection!,entry=this.entry;
    // Invalidate the old callback immediately, including pending subscription replies.
    this.stop();this.recovering=true;
    const retryGeneration=this.generation;
    this.retry=setTimeout(()=>{
      this.retry=undefined;
      if(retryGeneration!==this.generation||!this.recovering) return;
      this.recovering=false;this.start(connection,entry);
    },5000);
  }
  stop() {
    this.generation++;this.running=false;this.recovering=false;this.last=0;
    if(this.retry)clearTimeout(this.retry);if(this.watchdog)clearInterval(this.watchdog);
    this.retry=undefined;this.watchdog=undefined;
    const remove=this.unsubscribe;this.unsubscribe=undefined;
    if(remove)void Promise.resolve().then(()=>remove()).catch(()=>{});
  }
}
