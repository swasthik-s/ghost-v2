'use client';

import { useEffect, useMemo, useState } from 'react';
import dynamic from 'next/dynamic';
import {
  Activity, AlertTriangle, ArrowDownRight, ArrowUpRight, Bell, Bot, Cable,
  ChartNoAxesCombined, ChevronDown, CircleDollarSign, Code2, Database,
  FileCode2, FlaskConical, Gauge, LayoutDashboard, ListChecks, LockKeyhole,
  Menu, MoreHorizontal, Play, RefreshCw, Search, Settings2, Shield,
  SlidersHorizontal, Terminal, Wallet, X, Zap,
} from 'lucide-react';
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from 'recharts';

const MonacoEditor = dynamic(() => import('@monaco-editor/react'), { ssr: false });

type Page = 'Overview'|'Risk'|'Exposure'|'Alerts'|'Strategies'|'Backtests'|'Validation Lab'|'Data'|'MT5 Bridge'|'Code Workspace'|'Settings';

type BridgePosition = { ticket:number; symbol:string; side:'BUY'|'SELL'; volume:number; price_open:number; price_current:number; profit:number; swap:number; stop_loss:number; take_profit:number; magic:number; comment:string };
type BridgeSnapshot = {
  connected:boolean; data_source:string; age_seconds:number|null; stale_after_seconds:number;
  last_update:string|null; account?:{currency:string;balance:number;equity:number;floating_pnl:number;margin:number;free_margin:number;margin_level:number};
  positions:BridgePosition[]; terminal?:{connected:boolean;company?:string;server?:string;build?:number};
  execution_enabled:false; read_error?:string|null;
};
const API_BASE = process.env.NEXT_PUBLIC_GHOST_API_URL || '';
const fmtMoney = (value:number, currency:string) => new Intl.NumberFormat('en-US',{style:'currency',currency:currency||'USD',maximumFractionDigits:2}).format(value);

const nav: {group:string;items:{label:Page;icon:typeof Activity}[]}[] = [
  {group:'PLATFORM',items:[{label:'Overview',icon:LayoutDashboard}]},
  {group:'RISK MANAGEMENT',items:[{label:'Risk',icon:Shield},{label:'Exposure',icon:SlidersHorizontal},{label:'Alerts',icon:AlertTriangle}]},
  {group:'STRATEGY & RESEARCH',items:[{label:'Strategies',icon:Zap},{label:'Backtests',icon:FlaskConical},{label:'Validation Lab',icon:ListChecks},{label:'Data',icon:Database}]},
  {group:'CONNECTIVITY & TOOLS',items:[{label:'MT5 Bridge',icon:Cable},{label:'Code Workspace',icon:Code2}]},
  {group:'SYSTEM',items:[{label:'Settings',icon:Settings2}]},
];
const equity = Array.from({length:46},(_,i)=>({n:i,e:100000+i*255+Math.sin(i*.72)*520+Math.cos(i*.23)*370}));
const pnl = [{d:'Jun',v:1120},{d:'Jul',v:-420},{d:'Aug',v:1840},{d:'Sep',v:760},{d:'Oct',v:2210},{d:'Nov',v:1247}];
const trades = [
  {time:'13:42:18',side:'BUY',symbol:'XAUUSD',strategy:'PRECISION_SNIPER',lots:'0.02',price:'2684.32',pnl:'+$84.20'},
  {time:'13:18:04',side:'SELL',symbol:'XAUUSD',strategy:'INTRADAY_MOMENTUM',lots:'0.01',price:'2690.10',pnl:'+$31.40'},
  {time:'12:56:42',side:'BUY',symbol:'XAUUSD',strategy:'PRECISION_SNIPER',lots:'0.01',price:'2677.80',pnl:'-$12.60'},
  {time:'11:30:09',side:'SELL',symbol:'XAUUSD',strategy:'INTRADAY_MOMENTUM',lots:'0.01',price:'2689.22',pnl:'+$44.70'},
];
const strategies = [
  {name:'Precision Sniper',key:'PRECISION_SNIPER',desc:'Selective sweep, reclaim and displacement entries.',status:'READY',trades:'60',pf:'1.45',risk:'0.50%'},
  {name:'Intraday Momentum',key:'INTRADAY_MOMENTUM',desc:'EMA alignment, breakout and volatility filter hypothesis.',status:'STANDBY',trades:'—',pf:'—',risk:'0.25%'},
  {name:'SuperTrend Grid',key:'SUPERTREND_GRID',desc:'Favourable-direction pyramiding with strict exposure caps.',status:'STANDBY',trades:'—',pf:'—',risk:'0.25%'},
  {name:'Origin Ladder',key:'ORIGIN_LADDER',desc:'Experimental hypothesis, not a reverse-engineered clone.',status:'EXPERIMENTAL',trades:'—',pf:'—',risk:'0.25%'},
];
const py = `"""GHOST Python research workspace — starter only."""
from typing import Literal

Strategy = Literal[
    "PRECISION_SNIPER",
    "INTRADAY_MOMENTUM",
    "SUPERTREND_GRID",
    "ORIGIN_LADDER",
]

def evaluate(strategy: Strategy, symbol: str = "XAUUSD") -> dict:
    # No live order execution is performed in this module.
    return {
        "strategy": strategy,
        "symbol": symbol,
        "decision": "WAIT",
        "execution_allowed": False,
        "reason": "Research adapter and trusted market data are not connected.",
    }

if __name__ == "__main__":
    print(evaluate("PRECISION_SNIPER"))
`;
const mq = `// GHOST v2 — safe MT5 workspace starter
#property strict
#property version "0.1.0"
#include <Trade/Trade.mqh>
CTrade trade;

enum GHOST_MODE {
  PRECISION_SNIPER=0,
  INTRADAY_MOMENTUM=1,
  SUPERTREND_GRID=2,
  ORIGIN_LADDER=3
};
input GHOST_MODE InpStrategy=PRECISION_SNIPER;
input double InpRiskPerTradePct=0.50;
input double InpMaxDailyLossPct=2.00;
input double InpMaxDrawdownPct=5.00;
input int InpMaxPositions=3;

int OnInit() {
  Print("GHOST v2 safe starter loaded. No orders are sent.");
  return INIT_SUCCEEDED;
}
void OnTick() {
  // TODO: validated signal adapter + independent risk governor.
  // Fail closed: no order execution is implemented in this starter.
}
`;

function Pill({children,tone='neutral'}:{children:React.ReactNode;tone?:string}) { return <span className={`pill ${tone}`}>{children}</span>; }
function Panel({title,subtitle,children,right}:{title:string;subtitle?:string;children:React.ReactNode;right?:React.ReactNode}) { return <section className="panel"><div className="panel-head"><div><h3>{title}</h3>{subtitle&&<p>{subtitle}</p>}</div>{right}</div>{children}</section>; }
function Metric({title,value,sub,icon:Icon,tone='blue',trend}:{title:string;value:string;sub:string;icon:typeof Activity;tone?:string;trend?:string}) { return <div className="metric"><div className={`metric-icon ${tone}`}><Icon size={18}/></div><div className="metric-copy"><label>{title}</label><strong>{value}</strong><small>{sub}</small></div>{trend&&<span className="trend">{trend}</span>}</div>; }

export default function Home() {
  const [view,setView]=useState<Page>('Overview');
  const [mobile,setMobile]=useState(false);
  const [strategy,setStrategy]=useState('PRECISION_SNIPER');
  const [file,setFile]=useState<'python'|'mql5'>('python');
  const [pythonCode,setPythonCode]=useState(py);
  const [mqlCode,setMqlCode]=useState(mq);
  const [output,setOutput]=useState('Workspace ready. Demo values only. Connect the local GHOST agent to enable persistence and research jobs.');
  const [notice,setNotice]=useState(true);
  const [range,setRange]=useState('1M');
  const [refreshNonce,setRefreshNonce]=useState(0);
  const [bridge,setBridge]=useState<BridgeSnapshot>({connected:false,data_source:'NONE',age_seconds:null,stale_after_seconds:10,last_update:null,positions:[],execution_enabled:false});
  const [liveEquity,setLiveEquity]=useState<{captured_at:number;equity:number;balance:number}[]>([]);
  useEffect(()=>{
    if(!API_BASE) return;
    let active=true;
    const poll=async()=>{
      try{
        const response=await fetch(`${API_BASE.replace(/\/$/,'')}/api/v1/snapshot`,{cache:'no-store'});
        if(!response.ok) throw new Error(`Bridge HTTP ${response.status}`);
        const data=await response.json() as BridgeSnapshot;
        if(active) setBridge(data);
        if(data.connected){
          try{
            const history=await fetch(`${API_BASE.replace(/\/$/,'')}/api/v1/equity?limit=300`,{cache:'no-store'});
            if(history.ok){
              const body=await history.json();
              if(active) setLiveEquity(Array.isArray(body.items)?body.items:[]);
            }
          }catch{/* Snapshot connectivity is independent from chart history. */}
        }
      }catch{
        if(active) setBridge(prev=>({...prev,connected:false}));
      }
    };
    void poll();
    const timer=window.setInterval(()=>void poll(),3000);
    return()=>{active=false;window.clearInterval(timer);};
  },[refreshNonce]);
  const code=file==='python'?pythonCode:mqlCode;
  const setCode=file==='python'?setPythonCode:setMqlCode;
  const chart=useMemo(()=>{
    if(bridge.connected) return liveEquity.length>1?liveEquity.map((item,index)=>({n:index,e:item.equity})):[];
    return equity.map(x=>({...x,e:x.e}));
  },[bridge.connected,liveEquity]);
  const title=view==='Overview'?'Trading overview':view;
  const say=(s:string)=>setOutput(s);

  return <div className="shell">
    <aside className={`sidebar ${mobile?'open':''}`}>
      <div className="brand"><span className="brand-icon"><Bot size={20}/></span><b>GHOST</b><small>V2</small><button className="mobile-close" onClick={()=>setMobile(false)}><X size={17}/></button></div>
      <div className="workspace"><span>G</span><div><b>GHOST TERMINAL</b><small>Local research workspace</small></div><ChevronDown size={14}/></div>
      <nav>{nav.map(g=><div className="nav-group" key={g.group}><label>{g.group}</label>{g.items.map(item=><button key={item.label} className={view===item.label?'active':''} onClick={()=>{setView(item.label);setMobile(false)}}><item.icon size={16}/>{item.label}{item.label==='Alerts'&&<i>2</i>}</button>)}</div>)}</nav>
      <div className="side-bottom"><div className="bridge-mini"><div><i/> MT5 CONNECTION <Pill tone={bridge.connected?'green':'warn'}>{bridge.connected?'ONLINE':'OFFLINE'}</Pill></div><small>{bridge.connected?`Snapshot ${bridge.age_seconds??0}s ago`:'Waiting for local bridge agent'}</small><button onClick={()=>setView('MT5 Bridge')}>Configure connection <ArrowUpRight size={13}/></button></div><div className="operator"><span>S</span><div><b>Operator</b><small>Administrator</small></div><MoreHorizontal size={17}/></div></div>
    </aside>
    {mobile&&<button className="scrim" aria-label="Close menu" onClick={()=>setMobile(false)}/>}
    <main className="main">
      <header className="topbar"><div className="crumb"><button className="mobile-menu" onClick={()=>setMobile(true)}><Menu size={18}/></button>GHOST <span>/</span> {title.toUpperCase()}</div><div className="top-actions"><span className="demo"><i/> {bridge.connected?'MT5 FEED CONNECTED':'DEMO ENVIRONMENT'}</span><button title="Search"><Search size={17}/></button><button title="Notifications" onClick={()=>setView('Alerts')}><Bell size={17}/></button><span className="avatar">S</span></div></header>
      <div className="content">
        <div className="heading"><div><small>CONTROL CENTER / {view.toUpperCase()}</small><h1>{title}</h1><p>Account performance, execution activity and system health in one place.</p></div><div className="head-buttons"><Pill tone={bridge.connected?'green':'warn'}>{bridge.connected?'MT5 TELEMETRY':'SAMPLE METRICS'}</Pill><button className="btn" onClick={()=>{setNotice(true);setRefreshNonce(v=>v+1)}}><RefreshCw size={14}/> Refresh</button></div></div>
        {notice&&<div className="notice"><AlertTriangle size={15}/><b>{bridge.connected?'READ-ONLY MT5 TELEMETRY':'DEMO DATA · MT5 NOT CONNECTED'}</b><span>{bridge.connected?'Account and position metrics are sourced from the local MT5 exporter. Order execution is disabled.':'Numbers shown are illustrative, not broker account data. Configure the local Python bridge to connect MT5.'}</span><button onClick={()=>setNotice(false)}><X size={14}/></button></div>}

        {view==='Overview'&&<>
          <div className="metrics four"><Metric title="ACCOUNT EQUITY" value={bridge.connected&&bridge.account?fmtMoney(bridge.account.equity,bridge.account.currency):"$10,847.21"} sub={bridge.connected&&bridge.account?`Balance ${fmtMoney(bridge.account.balance,bridge.account.currency)}`:"Balance $10,700.00 · sample"} icon={Wallet} trend={bridge.connected?'MT5':'SAMPLE'}/><Metric title={bridge.connected?'FLOATING P&L':"TODAY'S P&L"} value={bridge.connected&&bridge.account?fmtMoney(bridge.account.floating_pnl,bridge.account.currency):"+$147.32"} sub={bridge.connected?"Open-position P&L from MT5":"3 closed trades · demo sample"} icon={CircleDollarSign} tone="green"/><Metric title="MARGIN LEVEL" value={bridge.connected&&bridge.account?`${bridge.account.margin_level.toFixed(1)}%`:"—"} sub={bridge.connected&&bridge.account?`Free margin ${fmtMoney(bridge.account.free_margin,bridge.account.currency)}`:"Connect MT5 for account metrics"} icon={Gauge} tone="violet"/><Metric title="OPEN POSITIONS" value={bridge.connected?String(bridge.positions.length):"2"} sub={bridge.connected?`${bridge.positions.reduce((sum,p)=>sum+p.volume,0).toFixed(2)} lots · MT5`:"0.03 lots · sample"} icon={Activity} tone="amber"/></div>
          <Panel title="EQUITY CURVE" subtitle={bridge.connected?(liveEquity.length>1?'MT5 account equity history':'Connected · collecting equity history'):'Account equity · illustrative sample series'} right={<div className="ranges">{['1D','1W','1M','ALL'].map(r=><button className={range===r?'selected':''} onClick={()=>setRange(r)} key={r}>{r}</button>)}</div>}><div className="chart-total">{bridge.connected&&bridge.account?fmtMoney(bridge.account.equity,bridge.account.currency):'$10,847.21'} {!bridge.connected&&<span className="positive">SAMPLE</span>}</div><div className="equity-chart"><ResponsiveContainer width="100%" height="100%"><AreaChart data={chart}><defs><linearGradient id="equityFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#8d68ef" stopOpacity={.30}/><stop offset="100%" stopColor="#8d68ef" stopOpacity={0}/></linearGradient></defs><CartesianGrid stroke="#202a38" vertical={false}/><XAxis dataKey="n" hide/><YAxis hide domain={['dataMin-500','dataMax+500']}/><Tooltip contentStyle={{background:'#101722',border:'1px solid #344052',borderRadius:7}}/><Area dataKey="e" type="monotone" stroke="#9875ff" strokeWidth={2} fill="url(#equityFill)"/></AreaChart></ResponsiveContainer></div></Panel>
          <div className="columns"><Panel title="EXECUTION LOG" subtitle="Recent strategy activity · sample records until deal-history export is enabled"><div className="table-wrap"><table><thead><tr><th>TIME</th><th>SIDE</th><th>SYMBOL</th><th>STRATEGY</th><th>LOTS</th><th>P&L</th></tr></thead><tbody>{trades.map((t,i)=><tr key={i}><td className="mono muted">{t.time}</td><td><Pill tone={t.side==='BUY'?'green':'red'}>{t.side}</Pill></td><td className="strong">{t.symbol}</td><td className="mono muted">{t.strategy}</td><td>{t.lots}</td><td className={t.pnl.startsWith('-')?'negative':'positive'}>{t.pnl}</td></tr>)}</tbody></table></div></Panel><Panel title="OPEN POSITIONS" subtitle={bridge.connected?"Positions from connected MT5 account":"Illustrative positions · sample"}>{bridge.connected?bridge.positions.length?bridge.positions.map((p)=><div className="position" key={p.ticket}><div><b>{p.symbol} <Pill tone={p.side==='BUY'?'green':'red'}>{p.side}</Pill></b><small>{p.volume.toFixed(2)} lots · Entry {p.price_open}</small></div><strong className={(p.profit+p.swap)>=0?'positive':'negative'}>{fmtMoney(p.profit+p.swap,bridge.account?.currency||'USD')}</strong></div>):<div className="muted small">No open positions reported by MT5.</div>:<><div className="position"><div><b>XAUUSD <Pill tone="green">BUY</Pill></b><small>0.02 lots · Entry 2684.32</small></div><strong className="positive">+$84.20</strong></div><div className="position"><div><b>XAUUSD <Pill tone="red">SELL</Pill></b><small>0.01 lots · Entry 2690.10</small></div><strong className="positive">+$31.40</strong></div></>}<div className="mini-stats"><span>FLOATING P&L</span><b className={bridge.connected&&bridge.account&&bridge.account.floating_pnl<0?'negative':'positive'}>{bridge.connected&&bridge.account?fmtMoney(bridge.account.floating_pnl,bridge.account.currency):'+$115.60'}</b></div></Panel></div>
          <div className="metrics four compact"><Metric title="RISK / TRADE" value="0.50%" sub="Configured in EA · not yet streamed" icon={Shield}/><Metric title="DAILY LOSS LIMIT" value="2.00%" sub="EA-side control · not yet streamed" icon={Shield} tone="red"/><Metric title="MAX DRAWDOWN" value="5.00%" sub="EA-side control · not yet streamed" icon={Gauge} tone="amber"/><Metric title="EXECUTION" value="DISABLED" sub="Telemetry-only bridge" icon={LockKeyhole} tone="violet"/></div>
        </>}

        {view==='Risk'&&<><div className="metrics four"><Metric title="CURRENT EQUITY" value={bridge.connected&&bridge.account?fmtMoney(bridge.account.equity,bridge.account.currency):"$10,847.21"} sub={bridge.connected?"MT5 account equity":"Sample equity"} icon={Wallet}/><Metric title="DAILY DRAWDOWN" value="NOT REPORTED" sub="EA risk telemetry not exported yet" icon={ArrowDownRight} tone="amber"/><Metric title="PEAK DRAWDOWN" value="NOT REPORTED" sub="EA high-water mark not exported yet" icon={Gauge} tone="violet"/><Metric title="RISK STATUS" value="UNKNOWN" sub="Telemetry-only bridge" icon={Shield} tone="red"/></div><Panel title="RISK GOVERNOR" subtitle="Risk limits must be read from the EA; account snapshots alone cannot establish remaining risk capacity"><div className="alert-row"><Shield/><div><b>Risk telemetry not yet available</b><small>The exporter currently reports account and position data only. Daily loss, high-water drawdown, configured risk and breach state will be added through a separate EA telemetry contract.</small></div><Pill tone="warn">NOT REPORTED</Pill></div></Panel></>}
        {view==='Exposure'&&<Panel title="EXPOSURE MONITOR" subtitle={bridge.connected?"Current open positions from MT5":"Sample exposure · MT5 not connected"}><div className="table-wrap"><table><thead><tr><th>SYMBOL</th><th>DIRECTION</th><th>VOLUME</th><th>OPEN P&L</th><th>MAGIC / COMMENT</th><th>STATE</th></tr></thead><tbody>{bridge.connected?bridge.positions.map(p=><tr key={p.ticket}><td>{p.symbol}</td><td>{p.side}</td><td>{p.volume.toFixed(2)}</td><td className={(p.profit+p.swap)>=0?'positive':'negative'}>{fmtMoney(p.profit+p.swap,bridge.account?.currency||'USD')}</td><td className="mono">{p.magic} / {p.comment||'—'}</td><td><Pill tone="green">MT5</Pill></td></tr>):trades.slice(0,2).map((t,i)=><tr key={i}><td>{t.symbol}</td><td>{t.side}</td><td>{t.lots}</td><td className={t.pnl.startsWith('-')?'negative':'positive'}>{t.pnl}</td><td className="mono">{t.strategy}</td><td><Pill tone="warn">SAMPLE</Pill></td></tr>)}</tbody></table></div>{bridge.connected&&bridge.positions.length===0&&<p className="muted small">No open positions reported by the MT5 exporter.</p>}</Panel>}
        {view==='Alerts'&&<Panel title="RISK & SYSTEM ALERTS" subtitle="Current system notifications">{!bridge.connected&&<div className="alert-row"><AlertTriangle/><div><b>MT5 bridge is not connected</b><small>Dashboard is running in sample mode; no broker data is available.</small></div><Pill tone="warn">WARNING</Pill></div>}{bridge.connected&&<div className="alert-row"><Activity/><div><b>MT5 telemetry connected</b><small>Read-only snapshot received {bridge.age_seconds??0} seconds ago. Order execution remains disabled.</small></div><Pill tone="green">ONLINE</Pill></div>}<div className="alert-row"><Activity/><div><b>Risk telemetry incomplete</b><small>Daily loss, equity high-water drawdown and EA governor state are not yet exported.</small></div><Pill tone="warn">INFO</Pill></div><div className="alert-row"><Database/><div><b>Research history</b><small>Equity snapshots are stored locally in SQLite; trade/deal history export is still pending.</small></div><Pill tone="blue">INFO</Pill></div></Panel>}
        {view==='Strategies'&&<div className="strategy-grid">{strategies.map(s=><article className="strategy" key={s.key}><div className="strategy-top"><span className="strategy-icon"><Zap size={18}/></span><Pill tone={s.status==='READY'?'green':s.status==='EXPERIMENTAL'?'violet':'neutral'}>{s.status}</Pill></div><h3>{s.name}</h3><p>{s.desc}</p><div className="strategy-stats"><div><small>TRADES</small><b>{s.trades}</b></div><div><small>PROFIT FACTOR</small><b>{s.pf}</b></div><div><small>RISK / TRADE</small><b>{s.risk}</b></div></div><button className={strategy===s.key?'btn primary':'btn'} onClick={()=>{setStrategy(s.key);say(`${s.name} selected. Trading remains disabled until MT5 connection and risk checks are implemented.`)}}>{strategy===s.key?'SELECTED':'SELECT STRATEGY'}</button></article>)}</div>}
        {view==='Backtests'&&<><div className="metrics three"><Metric title="LAST TEST" value="SNIPER V0.1" sub="XAUUSD · M5" icon={FlaskConical}/><Metric title="NET PROFIT" value="+$84.11" sub="On $10,000 start" icon={CircleDollarSign} tone="green"/><Metric title="PROFIT FACTOR" value="1.45" sub="60 trades · small sample" icon={ChartNoAxesCombined} tone="violet"/></div><Panel title="BACKTEST RUNNER" subtitle="Prepared for the local Python research worker"><div className="form-grid"><label>Strategy<select value={strategy} onChange={e=>setStrategy(e.target.value)}>{strategies.map(s=><option key={s.key} value={s.key}>{s.name}</option>)}</select></label><label>Symbol<select defaultValue="XAUUSD"><option>XAUUSD</option></select></label><label>Timeframe<select defaultValue="M5"><option>M5</option><option>M15</option><option>H1</option></select></label><label>Initial capital<input defaultValue="10000"/></label></div><button className="btn primary" onClick={()=>say('Backtest request prepared. A local Python worker and imported historical data are required to run it.') }><Play size={14}/> Prepare backtest</button></Panel></>}
        {view==='Validation Lab'&&<div className="validation-grid">{[['Sensitivity Analysis','Parameter neighbourhoods, stability plateaus and fragile optimum detection.'],['Walk-Forward Analysis','Rolling calibration and strictly unseen out-of-sample evaluation.'],['Monte Carlo Simulation','Trade-sequence bootstrap, cost stress and drawdown breach probabilities.']].map(x=><article className="strategy" key={x[0]}><FlaskConical/><h3>{x[0]}</h3><p>{x[1]}</p><Pill tone="blue">PLANNED</Pill></article>)}</div>}
        {view==='Data'&&<Panel title="MARKET DATASETS" subtitle="Research data catalogue"><div className="alert-row"><Database/><div><b>XAUUSD M5 bars</b><small>Historical OHLC · import required</small></div><Pill tone="warn">NOT LOADED</Pill></div><div className="alert-row"><Activity/><div><b>XAUUSD tick history</b><small>Bid/ask tick data · broker source required</small></div><Pill tone="warn">NOT LOADED</Pill></div><div className="alert-row"><ListChecks/><div><b>MT5 trade records</b><small>CSV / JSON export</small></div><Pill tone="warn">NOT LOADED</Pill></div></Panel>}
        {view==='MT5 Bridge'&&<><div className="metrics three"><Metric title="TERMINAL" value={bridge.connected?"CONNECTED":"OFFLINE"} sub={bridge.connected?`Snapshot age ${bridge.age_seconds??0}s`:"No fresh exporter file"} icon={Cable} tone={bridge.connected?"green":"red"}/><Metric title="DATA FEED" value={bridge.connected?"STREAMING":"WAITING"} sub={bridge.last_update||"No telemetry received"} icon={Activity} tone={bridge.connected?"green":"amber"}/><Metric title="EXECUTION" value="LOCKED" sub="This bridge is read-only" icon={LockKeyhole} tone="violet"/></div><Panel title="WINDOWS MT5 LOCAL AGENT" subtitle="Read-only exporter → Common Files → Python API → dashboard"><div className="risk-row"><div><b>API connection</b><small>{API_BASE||"NEXT_PUBLIC_GHOST_API_URL not configured"}</small></div><div className="bar"><i style={{width:bridge.connected?'100%':'0%'}}/></div><code>{bridge.connected?"ONLINE":"OFFLINE"}</code></div><div className="risk-row"><div><b>Snapshot freshness</b><small>{bridge.age_seconds===null?"No snapshot":`${bridge.age_seconds}s old · stale threshold ${bridge.stale_after_seconds}s`}</small></div><div className="bar"><i style={{width:bridge.connected?'100%':'0%',background:bridge.connected?'#4cc99b':'#d7aa4c'}}/></div><code>{bridge.connected?"FRESH":"STALE"}</code></div><ol className="steps"><li>Compile and attach <code>GHOST_Bridge_Exporter.mq5</code> in MetaEditor. It exports telemetry only.</li><li>Start the local service from <code>local_agent</code>: <code>uvicorn main:app --host 127.0.0.1 --port 8765</code>.</li><li>For local Next.js development, set <code>NEXT_PUBLIC_GHOST_API_URL=http://127.0.0.1:8765</code> and restart Next.js.</li><li>Open <code>/api/v1/snapshot</code> to inspect account and positions. Disconnects become stale after 10 seconds.</li></ol><Pill tone={bridge.connected?"green":"warn"}>{bridge.connected?"READ-ONLY TELEMETRY CONNECTED":"WAITING FOR LOCAL EXPORTER"}</Pill></Panel></>}
        {view==='Code Workspace'&&<div className="code-grid"><Panel title="PROJECT EXPLORER" subtitle="GHOST V2 / WORKSPACE"><button className={file==='python'?'file active':'file'} onClick={()=>setFile('python')}><FileCode2 size={14}/> python / engine.py</button><button className={file==='mql5'?'file active':'file'} onClick={()=>setFile('mql5')}><FileCode2 size={14}/> mt5 / GHOST_v2.mq5</button><p className="muted small">Editor contents are currently held in browser memory. Persistence will require the local agent.</p></Panel><div className="editor"><div className="editor-head"><div><button className={file==='python'?'selected':''} onClick={()=>setFile('python')}>engine.py</button><button className={file==='mql5'?'selected':''} onClick={()=>setFile('mql5')}>GHOST_v2.mq5</button></div><div><button className="btn" onClick={()=>say('Saved in browser workspace only. Connect the local agent for filesystem persistence.')}>Save</button><button className="btn primary" onClick={()=>say(file==='python'?'Python run requires the local research worker. No code was executed.':'Compile request requires MetaEditor on the Windows MT5 machine. No compilation was run.')}><Play size={13}/>{file==='python'?'Run':'Compile'}</button></div></div><div className="editor-box"><MonacoEditor height="440px" language={file==='python'?'python':'cpp'} theme="vs-dark" value={code} onChange={v=>setCode(v??'')} options={{minimap:{enabled:false},fontSize:13,automaticLayout:true,scrollBeyondLastLine:false,tabSize:4,padding:{top:14}}}/></div><div className="terminal"><span><Terminal size={13}/> OUTPUT / TERMINAL</span>{output}</div></div></div>}
        {view==='Settings'&&<Panel title="RISK & EXECUTION SETTINGS" subtitle="Illustrative defaults · no broker effect"><div className="form-grid"><label>Risk per trade (%)<input defaultValue="0.50"/></label><label>Daily loss limit (%)<input defaultValue="2.00"/></label><label>Maximum drawdown (%)<input defaultValue="5.00"/></label><label>Maximum open positions<input defaultValue="3"/></label><label>Maximum total lots<input defaultValue="0.03"/></label><label>Mode<select defaultValue="DEMO"><option>DEMO</option><option disabled>LIVE — locked</option></select></label></div><Pill tone="warn">CONFIGURATION NOT CONNECTED</Pill></Panel>}
        <footer>GHOST V2 <b>0.1.0</b><span>LOCAL-FIRST · RISK GOVERNOR HAS FINAL AUTHORITY</span><span>© 2026 GHOST PROJECT</span></footer>
      </div>
    </main>
  </div>;
}
