import { useState } from 'react';
import { useLocalStorage } from '../../hooks/useLocalStorage';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  AreaChart, Area, BarChart, Bar, Cell
} from 'recharts';

const defaultFollowerData = [
  { month: 'Jan', followers: 420 },
  { month: 'Feb', followers: 680 },
  { month: 'Mar', followers: 1020 },
  { month: 'Apr', followers: 1450 },
  { month: 'May', followers: 2100 },
  { month: 'Jun', followers: 2975 },
];

const defaultViewsData = [
  { month: 'Jan', views: 45000 },
  { month: 'Feb', views: 89000 },
  { month: 'Mar', views: 210000 },
  { month: 'Apr', views: 540000 },
  { month: 'May', views: 890000 },
  { month: 'Jun', views: 1300000 },
];

const defaultRevenueData = [
  { month: 'Apr', revenue: 35 },
  { month: 'May', revenue: 90 },
  { month: 'Jun', revenue: 155 },
];

const milestones = [
  { label: '5K Followers', target: 5000, current: 2975, icon: '👥', timeEst: '~6 weeks', tips: 'Post daily, use viral formula captions, engage with comments in first 30 min' },
  { label: '10K Followers', target: 10000, current: 2975, icon: '🎯', timeEst: '~3 months', tips: 'Unlock Instagram link in Stories at 10K — massive for affiliate marketing' },
  { label: '1M Reel Views', target: 1000000, current: 557000, icon: '🔥', timeEst: 'Already 557K best reel!', tips: 'Your 557K reel puts you on track. Next viral: dog + baby emotional hook' },
  { label: '£500 Revenue', target: 500, current: 190, icon: '💰', timeEst: '~1 month', tips: 'One brand deal (£250) + 7 portrait orders (£35 each) = £495. So close!' },
  { label: 'First Brand Deal', target: 1, current: 0, icon: '🤝', timeEst: 'This week!', tips: 'Send 5 emails from Collab Hub today. With 1.3M views, you deserve YES.' },
  { label: '100K Monthly Views', target: 100000, current: 1300000, icon: '📈', timeEst: 'ACHIEVED ✅', tips: 'You\'ve hit 1.3M! Goal 10× completed. New goal: 5M monthly views.' },
];

function pct(current, target) {
  return Math.min(100, Math.round((current / target) * 100));
}

function fmtNum(n) {
  if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
  if (n >= 1000) return (n / 1000).toFixed(0) + 'K';
  return n.toString();
}

const COLORS = ['#F5A623', '#A855F7', '#22C55E', '#60A5FA', '#EF4444', '#EAB308'];

export default function GrowthTracker() {
  const [followerData, setFollowerData] = useLocalStorage('follower_data', defaultFollowerData);
  const [viewsData] = useLocalStorage('views_data', defaultViewsData);
  const [revenueData] = useLocalStorage('revenue_data', defaultRevenueData);
  const [activeTab, setActiveTab] = useState('charts');
  const [addFollowers, setAddFollowers] = useState({ month: '', followers: '' });
  const [showAdd, setShowAdd] = useState(false);

  const latestFollowers = followerData[followerData.length - 1]?.followers || 0;
  const prevFollowers = followerData[followerData.length - 2]?.followers || 0;
  const followerGrowth = latestFollowers - prevFollowers;
  const growthRate = prevFollowers ? ((followerGrowth / prevFollowers) * 100).toFixed(1) : 0;
  const daysTo5K = Math.ceil((5000 - latestFollowers) / (followerGrowth / 30));
  const latestViews = viewsData[viewsData.length - 1]?.views || 0;
  const latestRevenue = revenueData[revenueData.length - 1]?.revenue || 0;

  const chartTooltipStyle = {
    contentStyle: { background: '#161618', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 8, fontSize: 12 },
    labelStyle: { color: '#F0EDE8' },
    itemStyle: { color: '#F5A623' },
  };

  return (
    <div className="section-wrapper">
      <div className="section-header">
        <h1 className="section-title">📈 Growth Tracker</h1>
        <p className="section-subtitle">Follower & views growth · Revenue tracker · Milestone countdown · Goals</p>
      </div>

      {/* Summary KPIs */}
      <div className="grid-4 mb-20">
        <div className="metric-card">
          <div className="metric-icon">👥</div>
          <div className="metric-value">{fmtNum(latestFollowers)}</div>
          <div className="metric-label">Followers</div>
          <div className="metric-change up">+{followerGrowth} this month (+{growthRate}%)</div>
        </div>
        <div className="metric-card">
          <div className="metric-icon">👀</div>
          <div className="metric-value">{fmtNum(latestViews)}</div>
          <div className="metric-label">Monthly Views</div>
          <div className="metric-change up">↑ All-time high</div>
        </div>
        <div className="metric-card">
          <div className="metric-icon">💷</div>
          <div className="metric-value">£{latestRevenue}</div>
          <div className="metric-label">Monthly Revenue</div>
          <div className="metric-change up">↑ Growing</div>
        </div>
        <div className="metric-card">
          <div className="metric-icon">⏳</div>
          <div className="metric-value">{daysTo5K > 0 ? daysTo5K + 'd' : 'Done!'}</div>
          <div className="metric-label">Days to 5K Followers</div>
          <div className="metric-change up">At current pace</div>
        </div>
      </div>

      <div className="tabs">
        {[['charts', '📊 Growth Charts'], ['milestones', '🏆 Milestones'], ['goals', '🎯 Goals']].map(([k, l]) => (
          <button key={k} className={`tab ${activeTab === k ? 'active' : ''}`} onClick={() => setActiveTab(k)}>{l}</button>
        ))}
      </div>

      {activeTab === 'charts' && (
        <>
          <div className="grid-2 mb-20">
            <div className="chart-container">
              <div className="chart-header">
                <span className="chart-title">👥 Follower Growth</span>
                <button className="btn btn-outline btn-sm" onClick={() => setShowAdd(!showAdd)}>+ Update</button>
              </div>
              {showAdd && (
                <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
                  <input placeholder="Month (e.g. Jul)" value={addFollowers.month} onChange={e => setAddFollowers({ ...addFollowers, month: e.target.value })} style={{ width: 100 }} />
                  <input type="number" placeholder="Followers" value={addFollowers.followers} onChange={e => setAddFollowers({ ...addFollowers, followers: e.target.value })} style={{ width: 120 }} />
                  <button className="btn btn-gold btn-sm" onClick={() => {
                    if (!addFollowers.month || !addFollowers.followers) return;
                    setFollowerData([...followerData, { month: addFollowers.month, followers: +addFollowers.followers }]);
                    setAddFollowers({ month: '', followers: '' });
                    setShowAdd(false);
                  }}>Add</button>
                </div>
              )}
              <ResponsiveContainer width="100%" height={220}>
                <AreaChart data={followerData}>
                  <defs>
                    <linearGradient id="goldGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#F5A623" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#F5A623" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="month" tick={{ fill: '#5C5A57', fontSize: 11 }} />
                  <YAxis tick={{ fill: '#5C5A57', fontSize: 11 }} />
                  <Tooltip {...chartTooltipStyle} formatter={(v) => [v.toLocaleString(), 'Followers']} />
                  <Area type="monotone" dataKey="followers" stroke="#F5A623" strokeWidth={2.5} fill="url(#goldGrad)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            <div className="chart-container">
              <div className="chart-header">
                <span className="chart-title">👀 Views Growth</span>
                <span className="badge badge-green">+45% MoM</span>
              </div>
              <ResponsiveContainer width="100%" height={220}>
                <AreaChart data={viewsData}>
                  <defs>
                    <linearGradient id="blueGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#60A5FA" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#60A5FA" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="month" tick={{ fill: '#5C5A57', fontSize: 11 }} />
                  <YAxis tick={{ fill: '#5C5A57', fontSize: 11 }} tickFormatter={v => fmtNum(v)} />
                  <Tooltip {...chartTooltipStyle} formatter={(v) => [fmtNum(v), 'Views']} />
                  <Area type="monotone" dataKey="views" stroke="#60A5FA" strokeWidth={2.5} fill="url(#blueGrad)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="chart-container mb-20">
            <div className="chart-header">
              <span className="chart-title">💷 Revenue Growth (£)</span>
              <span className="badge badge-gold">Building momentum 🚀</span>
            </div>
            <ResponsiveContainer width="100%" height={160}>
              <BarChart data={revenueData} barSize={40}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="month" tick={{ fill: '#5C5A57', fontSize: 11 }} />
                <YAxis tick={{ fill: '#5C5A57', fontSize: 11 }} />
                <Tooltip {...chartTooltipStyle} formatter={(v) => ['£' + v, 'Revenue']} />
                <Bar dataKey="revenue" fill="#F5A623" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="card">
            <div className="card-title">📊 Growth Summary</div>
            <div className="grid-3">
              {[
                { label: 'Monthly Follower Growth Rate', value: `+${growthRate}%`, note: 'vs previous month', color: 'var(--green)' },
                { label: 'Views per Follower (ratio)', value: '~437×', note: 'Exceptional for your size', color: 'var(--gold)' },
                { label: 'Estimated Reach Multiplier', value: '13×', note: 'vs typical creator at your size', color: 'var(--purple)' },
                { label: 'Content Velocity', value: '7/week', note: 'Daily posting consistency', color: 'var(--blue)' },
                { label: 'Viral Hit Rate', value: '25%', note: '1 in 4 posts goes viral (150K+)', color: 'var(--gold)' },
                { label: 'Projected Followers (90d)', value: fmtNum(Math.round(latestFollowers * 2.8)), note: 'At current pace', color: 'var(--green)' },
              ].map((s, i) => (
                <div key={i} style={{ background: 'var(--bg-card2)', borderRadius: 10, padding: '14px 16px', border: '1px solid var(--border)' }}>
                  <div style={{ fontSize: 22, fontWeight: 800, color: s.color, marginBottom: 4 }}>{s.value}</div>
                  <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 3 }}>{s.label}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{s.note}</div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {activeTab === 'milestones' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {milestones.map((m, i) => {
            const p = pct(m.current, m.target);
            const done = p >= 100;
            return (
              <div key={i} className="milestone-item" style={{ borderColor: done ? 'rgba(34,197,94,0.3)' : 'var(--border)' }}>
                <div className="milestone-info">
                  <div className="flex items-center gap-12">
                    <span style={{ fontSize: 22 }}>{m.icon}</span>
                    <div>
                      <div className="milestone-label">{m.label}</div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>⏱ {m.timeEst}</div>
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: 14, fontWeight: 700, color: done ? 'var(--green)' : 'var(--gold)' }}>
                      {done ? '✅ Complete!' : `${fmtNum(m.current)} / ${fmtNum(m.target)}`}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{p}%</div>
                  </div>
                </div>
                <div className="progress-bar">
                  <div className="progress-fill" style={{ width: `${p}%`, background: done ? 'var(--green)' : 'linear-gradient(90deg, var(--gold), var(--gold-light))' }}></div>
                </div>
                {!done && (
                  <div style={{ marginTop: 10, fontSize: 12, color: 'var(--text-secondary)', background: 'var(--bg-card2)', borderRadius: 7, padding: '8px 10px' }}>
                    💡 {m.tips}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {activeTab === 'goals' && (
        <>
          <div style={{ background: 'var(--gold-dim)', border: '1px solid var(--gold-border)', borderRadius: 10, padding: '12px 16px', marginBottom: 20, fontSize: 13, color: 'var(--text-primary)' }}>
            🎯 <strong style={{ color: 'var(--gold)' }}>Next milestone focus:</strong> 5K followers (est. {daysTo5K} days) + First brand deal this week
          </div>

          <div className="grid-3 mb-20">
            {[
              { icon: '🎯', title: '5K Followers', target: '5,000', timeline: '~6 weeks', action: 'Post daily, reply to every comment in first hour', color: 'var(--gold)' },
              { icon: '💰', title: 'First £500 Month', target: '£500/mo', timeline: '~4 weeks', action: 'Close 2 brand deals + 7 portrait orders', color: 'var(--green)' },
              { icon: '🤝', title: 'First Brand Deal', target: '1 Deal', timeline: 'This week!', action: 'Send 5 emails from Collab Hub today', color: 'var(--purple)' },
              { icon: '🔥', title: '1M View Reel', target: '1,000,000', timeline: '~4 weeks', action: 'Baby + dog emotional hook, 5:30am post', color: 'var(--red)' },
              { icon: '📦', title: 'First Digital Product', target: 'Live on Etsy', timeline: '~2 weeks', action: 'Create 50-prompt AI pack, list on Etsy', color: 'var(--blue)' },
              { icon: '📺', title: 'YouTube Channel Live', target: 'Channel Created', timeline: '~1 week', action: 'Repurpose top 3 reels as YouTube Shorts', color: 'var(--yellow)' },
            ].map((g, i) => (
              <div key={i} className="goal-card">
                <div className="goal-icon">{g.icon}</div>
                <div className="goal-title">{g.title}</div>
                <div className="goal-target" style={{ color: g.color }}>{g.target}</div>
                <div className="goal-timeline">{g.timeline}</div>
                <div style={{ marginTop: 10, fontSize: 11, color: 'var(--text-secondary)', lineHeight: 1.4 }}>{g.action}</div>
              </div>
            ))}
          </div>

          <div className="card">
            <div className="card-title">🗺️ 90-Day Growth Roadmap</div>
            <div style={{ position: 'relative' }}>
              {[
                { period: 'Weeks 1–2', items: ['Send 10 brand pitch emails (Collab Hub)', 'Create first digital product (prompt pack)', 'Set up YouTube channel + post first 3 Shorts', 'Add affiliate links to bio via Linktree'], color: '#F5A623' },
                { period: 'Weeks 3–4', items: ['Close first brand deal (follow up on pitches)', 'List prompt pack on Etsy + Gumroad', 'Hit 3,500 followers at current growth', 'Post portrait reveal reel to drive orders'], color: '#60A5FA' },
                { period: 'Month 2', items: ['Launch Patreon at 4K followers', 'Scale to 2 brand deals/month', 'Hit 4,500 followers', 'Start "How I made this" YouTube long-form'], color: '#A855F7' },
                { period: 'Month 3', items: ['Hit 5K followers milestone! 🎉', 'Unlock Instagram link in Stories', '£500–£800 monthly revenue target', 'Plan Patreon launch announcement reel'], color: '#22C55E' },
              ].map((phase, i) => (
                <div key={i} style={{ display: 'flex', gap: 16, marginBottom: 20 }}>
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                    <div style={{ width: 28, height: 28, borderRadius: '50%', background: phase.color, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#000', fontWeight: 700, fontSize: 12, minWidth: 28 }}>{i + 1}</div>
                    {i < 3 && <div style={{ width: 2, flex: 1, background: 'var(--border)', minHeight: 20 }}></div>}
                  </div>
                  <div style={{ flex: 1, paddingBottom: 8 }}>
                    <div style={{ fontSize: 14, fontWeight: 700, color: phase.color, marginBottom: 8 }}>{phase.period}</div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
                      {phase.items.map((item, j) => (
                        <div key={j} style={{ fontSize: 13, color: 'var(--text-secondary)', display: 'flex', gap: 7 }}>
                          <span style={{ color: phase.color }}>→</span>
                          <span>{item}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
