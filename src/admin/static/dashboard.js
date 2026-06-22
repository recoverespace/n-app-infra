(function(){
  var TENANT_ID = window.__DASHBOARD__.tenantId;
  var TENANTS = window.__DASHBOARD__.tenants;

  var grid = { color: 'rgba(120,110,90,0.10)' };
  var tick = { color: '#8A7E6B', font:{size:10} };
  var base = { responsive:true, maintainAspectRatio:false, plugins:{legend:{display:false}} };

  var trendChart = new Chart(document.getElementById('trendChart'), {
    type:'line',
    data:{ labels:[], datasets:[
      { label:'Mood', data:[], borderColor:'#1D9E75', tension:.35, pointRadius:3, pointHoverRadius:5, borderWidth:2, spanGaps:false },
      { label:'Stress', data:[], borderColor:'#D85A30', borderDash:[5,4], tension:.35, pointRadius:3, pointHoverRadius:5, borderWidth:2, spanGaps:false },
      { label:'Sleep', data:[], borderColor:'#C79A3B', borderDash:[2,3], tension:.35, pointRadius:3, pointHoverRadius:5, borderWidth:2, spanGaps:false }
    ]},
    options:Object.assign({}, base, {scales:{ y:{min:1,max:10,grid:grid,ticks:tick}, x:{grid:{display:false},ticks:tick} }})
  });

  var commChart = new Chart(document.getElementById('commChart'), {
    type:'bar',
    data:{ labels:[], datasets:[
      { label:'Reactions', data:[], backgroundColor:'#B6E8D7', maxBarThickness:48 },
      { label:'Comments', data:[], backgroundColor:'#5DCAA5', maxBarThickness:48 },
      { label:'Posts', data:[], backgroundColor:'#0F6E56', maxBarThickness:48 }
    ]},
    options:Object.assign({}, base, {scales:{ y:{stacked:true,min:0,grid:grid,ticks:Object.assign({}, tick, {stepSize:1, precision:0})}, x:{stacked:true,grid:{display:false},ticks:tick} }})
  });

  var aiChart = new Chart(document.getElementById('aiChart'), {
    type:'line',
    data:{ labels:[], datasets:[{ data:[], borderColor:'#534AB7', backgroundColor:'rgba(83,74,183,0.10)', fill:true, tension:.35, pointRadius:3, pointHoverRadius:5, borderWidth:2, spanGaps:false }]},
    options:Object.assign({}, base, {scales:{ y:{display:false,grid:{display:false}}, x:{grid:{display:false},ticks:tick} }})
  });

  function fmtNum(n){ return (n||0).toLocaleString('en-GB'); }

  function isoDate(d){
    var y=d.getFullYear(), m=('0'+(d.getMonth()+1)).slice(-2), day=('0'+d.getDate()).slice(-2);
    return y+'-'+m+'-'+day;
  }

  function academicYearStart(ref){
    var y=ref.getFullYear();
    if(ref.getMonth()>=8) return new Date(y,8,1);
    return new Date(y-1,8,1);
  }

  var currentRange = { from:null, to:null, label:'Last 30 days', win:'last 30 days' };

  function defaultRange(){
    var to=new Date(); to.setHours(23,59,59,999);
    var from=new Date(); from.setDate(from.getDate()-29); from.setHours(0,0,0,0);
    return { from:from, to:to, label:'Last 30 days', win:'last 30 days' };
  }

  function setDateInputs(from, to){
    document.getElementById('dFrom').value = isoDate(from);
    document.getElementById('dTo').value = isoDate(to);
  }

  function stackedCountMax(points){
    var max = 0;
    points.forEach(function(p){
      var total = (p.posts||0) + (p.comments||0) + (p.reactions||0);
      if (total > max) max = total;
    });
    return Math.max(5, Math.ceil(max * 1.15));
  }

  function applyData(data){
    var s=data.summary;
    document.getElementById('m-registered').textContent = fmtNum(s.total_registered);
    document.getElementById('m-active').textContent = fmtNum(s.active_users);
    document.getElementById('m-active-pct').textContent = s.active_pct+'%';
    document.getElementById('m-p2p').textContent = s.p2p_engagement_pct;
    document.getElementById('m-support').textContent = s.support_zone_pct;
    document.getElementById('m-ai-total').textContent = fmtNum(data.ai.total_reflections);
    document.getElementById('m-ai-pct').textContent = data.ai.engagement_pct+'%';

    document.getElementById('dateLabel').textContent = data.period.label;
    document.getElementById('m-active-window').textContent = currentRange.win;
    document.getElementById('themes-window').textContent = currentRange.win;

    var trend=data.wellbeing_trend||[];
    var hasTrend = trend.some(function(p){ return p.mood!=null || p.stress!=null || p.sleep!=null; });
    document.getElementById('trendEmpty').style.display = hasTrend?'none':'block';
    trendChart.data.labels = trend.map(function(p){return p.label;});
    trendChart.data.datasets[0].data = trend.map(function(p){return p.mood;});
    trendChart.data.datasets[1].data = trend.map(function(p){return p.stress;});
    trendChart.data.datasets[2].data = trend.map(function(p){return p.sleep;});
    trendChart.update();

    var comm=data.community||[];
    var commTotal = comm.reduce(function(sum, p){ return sum + (p.posts||0) + (p.comments||0) + (p.reactions||0); }, 0);
    document.getElementById('commEmpty').style.display = commTotal?'none':'block';
    commChart.data.labels = comm.map(function(p){return p.label;});
    commChart.data.datasets[0].data = comm.map(function(p){return p.reactions;});
    commChart.data.datasets[1].data = comm.map(function(p){return p.comments;});
    commChart.data.datasets[2].data = comm.map(function(p){return p.posts;});
    commChart.options.scales.y.max = stackedCountMax(comm);
    commChart.update();

    var aiTrend=data.ai.trend||[];
    aiChart.data.labels = aiTrend.map(function(p){return p.label;});
    aiChart.data.datasets[0].data = aiTrend.map(function(p){return p.count;});
    aiChart.update();

    var trackers=data.trackers||[];
    document.getElementById('trackers').innerHTML = trackers.length
      ? trackers.map(function(t){return '<div style="display:flex;align-items:center;gap:10px;margin-bottom:9px;"><span style="width:58px;font-size:12px;color:#8A7E6B;">'+t.name+'</span><div style="flex:1;height:8px;background:#F1EBE0;border-radius:4px;overflow:hidden;"><div style="width:'+t.pct+'%;height:100%;background:'+t.color+';border-radius:4px;"></div></div><span style="width:34px;text-align:right;font-size:12px;font-weight:500;">'+t.pct+'%</span></div>';}).join('')
      : '<p style="margin:0;font-size:11px;color:#8A7E6B;">No tracker data for this period</p>';

    var themes=data.themes||[];
    document.getElementById('themes').innerHTML = '<div style="display:flex;flex-wrap:wrap;gap:8px;">'+themes.map(function(t){var sz=11+Math.round(t.pct/4);return '<span style="font-size:'+sz+'px;background:#FBEBE2;color:#993C1D;padding:5px 11px;border-radius:8px;">'+t.name+' <span style="opacity:.65;font-size:11px;">'+t.pct+'%</span></span>';}).join('')+'</div>';

    var dims=data.dimensions||[];
    document.getElementById('dims').innerHTML = dims.length
      ? dims.map(function(d){var v=d.value!=null?d.value.toFixed(1):'—';var w=d.value!=null?d.value*10:0;return '<div style="background:#FBF7F0;border:0.5px solid #EEE6D8;border-radius:10px;padding:0.75rem;"><p style="margin:0;font-size:12px;color:#8A7E6B;">'+d.name+'</p><p style="margin:3px 0 6px;font-size:20px;font-weight:500;">'+v+'<span style="font-size:11px;color:#8A7E6B;">/10</span></p><div style="height:5px;background:#FFFFFF;border-radius:3px;overflow:hidden;"><div style="width:'+w+'%;height:100%;background:'+d.color+';"></div></div></div>';}).join('')
      : '<p style="margin:0;font-size:11px;color:#8A7E6B;">No dimension data for this period</p>';
  }

  function loadStats(){
    var overlay=document.getElementById('loadingOverlay');
    overlay.classList.add('visible');
    var params=new URLSearchParams({
      tenant_id: TENANT_ID,
      from: isoDate(currentRange.from),
      to: isoDate(currentRange.to),
      label: currentRange.label
    });
    fetch('/admin/dashboard/stats?'+params.toString())
      .then(function(r){ if(!r.ok) throw new Error('Failed to load'); return r.json(); })
      .then(applyData)
      .catch(function(){ console.error('Dashboard stats failed'); })
      .finally(function(){ overlay.classList.remove('visible'); });
  }

  function setRange(from, to, label, win){
    currentRange={from:from,to:to,label:label,win:win};
    setDateInputs(from,to);
    loadStats();
  }

  // Tenant switcher
  var tBtn=document.getElementById('tenantBtn');
  var tMenu=document.getElementById('tenantMenu');
  tMenu.innerHTML=TENANTS.map(function(t){return '<button role="option" data-id="'+t.id+'" style="display:block;width:100%;text-align:left;background:none;border:none;padding:8px 10px;border-radius:7px;cursor:pointer;font-family:inherit;font-size:14px;color:#2C2A26;">'+t.title+'</button>';}).join('');
  Array.prototype.forEach.call(tMenu.querySelectorAll('button'), function(b){
    b.addEventListener('mouseenter',function(){b.style.background='#F6F0E6';});
    b.addEventListener('mouseleave',function(){b.style.background='none';});
    b.addEventListener('click',function(){
      window.location.href='/admin/dashboard?tenant_id='+b.dataset.id;
    });
  });
  tBtn.addEventListener('click',function(e){
    e.stopPropagation();
    var open=tMenu.style.display==='block';
    closeAll(); tMenu.style.display=open?'none':'block';
    tBtn.setAttribute('aria-expanded', String(!open));
  });

  // Date filter
  var presets=[
    {id:'7', label:'Last 7 days', win:'last 7 days', days:7},
    {id:'30', label:'Last 30 days', win:'last 30 days', days:30},
    {id:'90', label:'Last 90 days', win:'last 90 days', days:90},
    {id:'term', label:'This term', win:'this term', days:120},
    {id:'ytd', label:'Academic year to date', win:'year to date', ytd:true}
  ];
  var dBtn=document.getElementById('dateBtn');
  var dMenu=document.getElementById('dateMenu');
  var presetList=document.getElementById('presetList');
  presetList.innerHTML=presets.map(function(p){return '<button data-id="'+p.id+'" style="display:flex;align-items:center;justify-content:space-between;width:100%;text-align:left;background:none;border:none;padding:8px 10px;border-radius:7px;cursor:pointer;font-family:inherit;font-size:13px;color:#2C2A26;">'+p.label+'<svg class="pcheck" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#D85A30" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="display:none;"><polyline points="20 6 9 17 4 12"></polyline></svg></button>';}).join('');

  function relabel(checkedId){
    Array.prototype.forEach.call(presetList.querySelectorAll('button'), function(b){
      b.querySelector('.pcheck').style.display=b.dataset.id===checkedId?'inline':'none';
    });
  }

  function applyPreset(p){
    var to=new Date(); to.setHours(23,59,59,999);
    var from;
    if(p.ytd){
      from=academicYearStart(to); from.setHours(0,0,0,0);
    } else {
      from=new Date(); from.setDate(from.getDate()-(p.days-1)); from.setHours(0,0,0,0);
    }
    setRange(from,to,p.label,p.win);
    relabel(p.id);
    dMenu.style.display='none'; dBtn.setAttribute('aria-expanded','false');
  }

  Array.prototype.forEach.call(presetList.querySelectorAll('button'), function(b){
    b.addEventListener('mouseenter',function(){b.style.background='#F6F0E6';});
    b.addEventListener('mouseleave',function(){b.style.background='none';});
    b.addEventListener('click',function(e){
      e.stopPropagation();
      var p=presets.filter(function(x){return x.id===b.dataset.id;})[0];
      applyPreset(p);
    });
  });

  document.getElementById('applyCustom').addEventListener('click',function(e){
    e.stopPropagation();
    var fromStr=document.getElementById('dFrom').value;
    var toStr=document.getElementById('dTo').value;
    if(!fromStr||!toStr) return;
    var from=new Date(fromStr+'T00:00:00');
    var to=new Date(toStr+'T23:59:59');
    function fmt(s){var d=new Date(s);return d.toLocaleDateString('en-GB',{day:'numeric',month:'short'});}
    var label=fmt(fromStr)+' \u2013 '+fmt(toStr);
    setRange(from,to,label,label);
    relabel(null);
    dMenu.style.display='none'; dBtn.setAttribute('aria-expanded','false');
  });

  dBtn.addEventListener('click',function(e){
    e.stopPropagation();
    var open=dMenu.style.display==='block';
    closeAll(); dMenu.style.display=open?'none':'block';
    dBtn.setAttribute('aria-expanded', String(!open));
  });
  dMenu.addEventListener('click',function(e){e.stopPropagation();});

  var infoText={
    support:'Share of active users whose check-ins in the selected period show low mood combined with high stress. Segments below the anonymity threshold are not shown.',
    trend_eng:'Source: daily wellbeing check-ins (mood, stress, sleep). Each point = mean of all check-in values in that bucket, scoped to the selected tenant + period, scale 1\u201310. Bucketed by day/week/month based on range length. Empty buckets skipped. Computed server-side over the populated set; users with no check-in in a bucket are excluded from that bucket only.',
    comm_eng:'Source: peer community event log. Counts of posts, comments and reactions created in each bucket, scoped to tenant + period. Each event counted once on its creation timestamp; deleted/removed content excluded. Stacked = total interactions. No content or author identity is read, counts only.',
    trackers_eng:'Source: tracker log entries. For each tracker, value = distinct active users who logged it at least once in the period, divided by active users in the period. A user counts once per tracker regardless of frequency. Sorted descending by that share. Tracker set is dynamic (reflects trackers live in the app).',
    ai_eng:'Source: AI reflection / check-in events. Count = total AI reflections in the period (every event). Reach % = distinct users with \u22651 AI event, divided by active users in the period. Trend line = AI events per bucket. Conversation content is never read; events are counted by type only.',
    themes_eng:'Source: peer conversations passed through a theme classifier. Value = share of conversations tagged with each theme in the period. A conversation may carry multiple themes. Only the aggregate tag counts are stored/returned; raw message text and per-message tags are never exposed. Themes below a minimum frequency are suppressed.',
    dims_eng:'Source: same check-in feed as the trend chart. Each tile = mean of that axis across all active users\u2019 check-ins in the period (latest value per user per day), scale 1\u201310. Connection and Focus are derived axes mapped from the loneliness and concentration check-in items.'
  };
  var pop=document.getElementById('infoPop');
  var openInfo=null;
  function hideInfo(){ pop.style.display='none'; openInfo=null; }
  function closeAll(){ hideInfo(); tMenu.style.display='none'; dMenu.style.display='none'; tBtn.setAttribute('aria-expanded','false'); dBtn.setAttribute('aria-expanded','false'); }
  Array.prototype.forEach.call(document.querySelectorAll('.info-btn, .corner-info'), function(b){
    b.addEventListener('click',function(e){
      e.stopPropagation();
      var key=b.dataset.info;
      if(openInfo===key){ hideInfo(); return; }
      closeAll();
      pop.textContent=infoText[key];
      pop.style.display='block';
      var shell=pop.parentElement.getBoundingClientRect();
      var r=b.getBoundingClientRect();
      var popW=280;
      var left=r.right-shell.left-popW;
      if(left<8) left=8;
      if(left+popW>shell.width-8) left=shell.width-popW-8;
      var top=r.bottom-shell.top+6;
      pop.style.left=left+'px';
      pop.style.top=top+'px';
      openInfo=key;
    });
  });
  document.addEventListener('click',closeAll);

  var init=defaultRange();
  currentRange=init;
  setDateInputs(init.from, init.to);
  relabel('30');
  loadStats();
})();
