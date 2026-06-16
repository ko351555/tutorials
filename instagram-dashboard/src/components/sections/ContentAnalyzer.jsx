import { useState } from 'react';
import { useLocalStorage } from '../../hooks/useLocalStorage';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell, Legend
} from 'recharts';

const defaultPosts = [
  { id: 1, title: 'Baby & Doggo Morning Cuddle', type: 'Reel', views: 557000, likes: 42100, comments: 1840, shares: 9200, date: '2026-06-10' },
  { id: 2, title: 'First Steps — I Held My Breath', type: 'Reel', views: 218000, likes: 19400, comments: 920, shares: 4100, date: '2026-06-08' },
  { id: 3, title: 'Sunday Family Pancakes', type: 'Reel', views: 145000, likes: 11200, comments: 540, shares: 2300, date: '2026-06-06' },
  { id: 4, title: 'Golden Hour Bedroom Moment', type: 'Reel', views: 98000, likes: 7800, comments: 380, shares: 1600, date: '2026-06-04' },
  { id: 5, title: 'Dog Protects Baby Photo', type: 'Carousel', views: 76000, likes: 6100, comments: 290, shares: 1100, date: '2026-06-02' },
  { id: 6, title: 'Kitchen Dance with Dad', type: 'Reel', views: 64000, likes: 5200, comments: 240, shares: 890, date: '2026-05-31' },
  { id: 7, title: 'Mum & Baby Nap Time', type: 'Photo', views: 38000, likes: 3200, comments: 180, shares: 520, date: '2026-05-29' },
  { id: 8, title: 'Weekly Caption Contest', type: 'Photo', views: 12000, likes: 980, comments: 410, shares: 120, date: '2026-05-27' },
];

const engagementTrend = [
  { week: 'Week 1', rate: 4.2 }, { week: 'Week 2', rate: 5.1 }, { week: 'Week 3', rate: 6.8 },
  { week: 'Week 4', rate: 7.4 }, { week: 'Week 5', rate: 9.1 }, { week: 'Week 6', rate: 8.6 },
  { week: 'Week 7', rate: 11.2 }, { week: 'Week 8', rate: 12.8 },
];

const contentMix = [
  { name: 'Reels', value: 68, color: '#F5A623' },
  { name: 'Photos', value: 18, color: '#60A5FA' },
  { name: 'Carousels', value: 14, color: '#A855F7' },
];

const timePerformance = [
  { time: '5:30am', views: 420 }, { time: '7am', views: 280 }, { time: '9am', views: 190 },
  { time: '12pm', views: 310 }, { time: '3pm', views: 260 }, { time: '6pm', views: 340 },
  { time: '9pm', views: 230 },
];

function getStatus(views) {
  if (views >= 150000) return 'viral';
  if (views >= 50000) return 'good';
  return 'low';
}

function fmtNum(n) {
  if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
  if (n >= 1000) return (n / 1000).toFixed(0) + 'K';
  return n.toString();
}

const VIRAL_COLOR = '#22C55E';
const GOOD_COLOR = '#EAB308';
const LOW_COLOR = '#EF4444';

export default function ContentAnalyzer() {
  const [posts, setPosts] = useLocalStorage('posts', defaultPosts);
  const [showAdd, setShowAdd] = useState(false);
  const [newPost, setNewPost] = useState({ title: '', type: 'Reel', views: '', likes: '', comments: '', shares: '', date: '' });

  const totalViews = posts.reduce((s, p) => s + p.views, 0);
  const totalLikes = posts.reduce((s, p) => s + p.likes, 0);
  const avgEng = posts.length ? ((totalLikes / totalViews) * 100).toFixed(1) : 0;
  const topPost = posts.reduce((a, b) => a.views > b.views ? a : b, posts[0] || {});
  const viralCount = posts.filter(p => getStatus(p.views) === 'viral').length;

  const addPost = () => {
    if (!newPost.title || !newPost.views) return;
    setPosts([{ ...newPost, id: Date.now(), views: +newPost.views, likes: +newPost.likes, comments: +newPost.comments, shares: +newPost.shares }, ...posts]);
    setNewPost({ title: '', type: 'Reel', views: '', likes: '', comments: '', shares: '', date: '' });
    setShowAdd(false);
  };

  const removePost = (id) => setPosts(posts.filter(p => p.id !== id));

  return (
    <div className="section-wrapper">
      <div className="section-header">
        <h1 className="section-title">📊 Content Analyzer</h1>
        <p className="section-subtitle">Track performance · Spot trends · Know what goes viral</p>
      </div>

      {/* KPI row */}
      <div className="grid-4 mb-20">
        <div className="metric-card">
          <div className="metric-icon">👀</div>
          <div className="metric-value">{fmtNum(totalViews)}</div>
          <div className="metric-label">Total Views (30d)</div>
          <div className="metric-change up">↑ +1.3M</div>
        </div>
        <div className="metric-card">
          <div className="metric-icon">❤️</div>
          <div className="metric-value">{fmtNum(totalLikes)}</div>
          <div className="metric-label">Total Likes</div>
          <div className="metric-change up">↑ Strong</div>
        </div>
        <div className="metric-card">
          <div className="metric-icon">📈</div>
          <div className="metric-value">{avgEng}%</div>
          <div className="metric-label">Avg Engagement Rate</div>
          <div className="metric-change up">↑ Top 5% niche</div>
        </div>
        <div className="metric-card">
          <div className="metric-icon">🔥</div>
          <div className="metric-value">{viralCount}</div>
          <div className="metric-label">Viral Posts (150K+)</div>
          <div className="metric-change up">↑ {Math.round((viralCount/posts.length)*100)}% hit rate</div>
        </div>
      </div>

      {/* Charts row */}
      <div className="grid-3 mb-20">
        <div className="chart-container" style={{ gridColumn: 'span 2' }}>
          <div className="chart-header">
            <span className="chart-title">📉 Engagement Rate Trend (%)</span>
            <span className="badge badge-green">↑ Trending Up</span>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={engagementTrend}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="week" tick={{ fill: '#5C5A57', fontSize: 11 }} />
              <YAxis tick={{ fill: '#5C5A57', fontSize: 11 }} />
              <Tooltip
                contentStyle={{ background: '#161618', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 8, fontSize: 12 }}
                labelStyle={{ color: '#F0EDE8' }}
                itemStyle={{ color: '#F5A623' }}
              />
              <Line type="monotone" dataKey="rate" stroke="#F5A623" strokeWidth={2.5} dot={{ fill: '#F5A623', r: 4 }} name="Eng %" />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-container">
          <div className="chart-header">
            <span className="chart-title">🎨 Content Mix</span>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={contentMix} cx="50%" cy="50%" innerRadius={55} outerRadius={80} paddingAngle={3} dataKey="value">
                {contentMix.map((entry, i) => <Cell key={i} fill={entry.color} />)}
              </Pie>
              <Legend iconType="circle" iconSize={8} formatter={(v) => <span style={{ color: '#A09D97', fontSize: 12 }}>{v}</span>} />
              <Tooltip contentStyle={{ background: '#161618', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 8, fontSize: 12 }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Best posting time */}
      <div className="chart-container mb-20">
        <div className="chart-header">
          <span className="chart-title">⏰ Best Posting Time Analysis (Avg views ×100)</span>
          <span className="badge badge-gold">5:30am wins 🏆</span>
        </div>
        <ResponsiveContainer width="100%" height={160}>
          <BarChart data={timePerformance} barSize={32}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis dataKey="time" tick={{ fill: '#5C5A57', fontSize: 11 }} />
            <YAxis tick={{ fill: '#5C5A57', fontSize: 11 }} />
            <Tooltip
              contentStyle={{ background: '#161618', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 8, fontSize: 12 }}
              labelStyle={{ color: '#F0EDE8' }}
              itemStyle={{ color: '#F5A623' }}
            />
            <Bar dataKey="views" name="Rel. Performance">
              {timePerformance.map((_, i) => (
                <Cell key={i} fill={i === 0 ? '#F5A623' : '#2A2A2D'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* What works / doesn't */}
      <div className="grid-2 mb-20">
        <div className="card">
          <div className="card-title">✅ What's Working</div>
          {[
            { emoji: '👶', text: 'Baby initiates love — drives 3× more shares' },
            { emoji: '🐶', text: 'Dog physically close to baby — emotional hook' },
            { emoji: '🛏️', text: 'Golden bedroom/kitchen lighting — visual appeal' },
            { emoji: '👨‍👩‍👧', text: 'All 4 family members in frame — community feel' },
            { emoji: '📝', text: '"I" narrative captions — first person connection' },
            { emoji: '⏰', text: '5:30am UK posting — catches morning scroll' },
            { emoji: '✂️', text: '3–5 punchy word lines — stops the scroll' },
            { emoji: '🎬', text: 'Reel format — 80% of your viral posts' },
          ].map((item, i) => (
            <div key={i} className="flex items-center gap-8 mb-8" style={{ padding: '6px 0', borderBottom: '1px solid var(--border)' }}>
              <span style={{ fontSize: 16, minWidth: 24 }}>{item.emoji}</span>
              <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{item.text}</span>
            </div>
          ))}
        </div>

        <div className="card">
          <div className="card-title">⚠️ What's Not Working</div>
          {[
            { emoji: '📸', text: 'Solo photo posts — avg 60% fewer views' },
            { emoji: '📝', text: 'Long captions over 3 lines — scroll past' },
            { emoji: '🌙', text: 'Evening posting (8–10pm) — lower reach' },
            { emoji: '🎭', text: 'Missing family member in frame' },
            { emoji: '#️⃣', text: 'Generic hashtags like #love #life' },
            { emoji: '🐾', text: 'Dog absent — drops engagement 40%' },
            { emoji: '📊', text: 'Tips/info content — not your niche strength' },
            { emoji: '🔇', text: 'Reels with no text overlay captions' },
          ].map((item, i) => (
            <div key={i} className="flex items-center gap-8 mb-8" style={{ padding: '6px 0', borderBottom: '1px solid var(--border)' }}>
              <span style={{ fontSize: 16, minWidth: 24 }}>{item.emoji}</span>
              <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{item.text}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Post tracker */}
      <div className="card">
        <div className="flex items-center justify-between mb-16">
          <div className="card-title" style={{ marginBottom: 0 }}>📋 Post Performance Tracker</div>
          <button className="btn btn-gold btn-sm" onClick={() => setShowAdd(!showAdd)}>
            {showAdd ? '✕ Cancel' : '＋ Add Post'}
          </button>
        </div>

        {showAdd && (
          <div className="card" style={{ marginBottom: 16, background: 'var(--bg-card2)' }}>
            <div className="form-row mb-12">
              <div className="form-group" style={{ marginBottom: 0, gridColumn: 'span 2' }}>
                <label>Post Title</label>
                <input placeholder="e.g. Baby & Dog Morning Cuddle" value={newPost.title} onChange={e => setNewPost({ ...newPost, title: e.target.value })} />
              </div>
            </div>
            <div className="form-row mb-12">
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label>Type</label>
                <select value={newPost.type} onChange={e => setNewPost({ ...newPost, type: e.target.value })}>
                  <option>Reel</option><option>Photo</option><option>Carousel</option><option>Story</option>
                </select>
              </div>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label>Date</label>
                <input type="date" value={newPost.date} onChange={e => setNewPost({ ...newPost, date: e.target.value })} />
              </div>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12, marginBottom: 14 }}>
              {['views', 'likes', 'comments', 'shares'].map(f => (
                <div key={f} className="form-group" style={{ marginBottom: 0 }}>
                  <label>{f}</label>
                  <input type="number" placeholder="0" value={newPost[f]} onChange={e => setNewPost({ ...newPost, [f]: e.target.value })} />
                </div>
              ))}
            </div>
            <button className="btn btn-gold" onClick={addPost}>Save Post</button>
          </div>
        )}

        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Post</th>
                <th>Type</th>
                <th>Views</th>
                <th>Likes</th>
                <th>Comments</th>
                <th>Shares</th>
                <th>Eng %</th>
                <th>Status</th>
                <th>Date</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {posts.map(post => {
                const status = getStatus(post.views);
                const eng = post.views ? ((post.likes / post.views) * 100).toFixed(1) : 0;
                return (
                  <tr key={post.id}>
                    <td style={{ fontWeight: 500, maxWidth: 200 }}>{post.title}</td>
                    <td><span className="badge badge-blue">{post.type}</span></td>
                    <td style={{ fontWeight: 700, color: status === 'viral' ? VIRAL_COLOR : status === 'good' ? GOOD_COLOR : 'var(--text-secondary)' }}>
                      {fmtNum(post.views)}
                    </td>
                    <td>{fmtNum(post.likes)}</td>
                    <td>{fmtNum(post.comments)}</td>
                    <td>{fmtNum(post.shares)}</td>
                    <td style={{ color: 'var(--gold)', fontWeight: 600 }}>{eng}%</td>
                    <td>
                      {status === 'viral' && <span className="badge badge-green">🔥 Viral</span>}
                      {status === 'good' && <span className="badge badge-yellow">⭐ Good</span>}
                      {status === 'low' && <span className="badge badge-red">📉 Low</span>}
                    </td>
                    <td style={{ color: 'var(--text-muted)', fontSize: 11 }}>{post.date}</td>
                    <td>
                      <button onClick={() => removePost(post.id)} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 14 }}>✕</button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div className="flex gap-16 mt-16" style={{ flexWrap: 'wrap' }}>
          <div className="flex items-center gap-8">
            <div style={{ width: 10, height: 10, borderRadius: '50%', background: VIRAL_COLOR }}></div>
            <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Viral: 150K+ views</span>
          </div>
          <div className="flex items-center gap-8">
            <div style={{ width: 10, height: 10, borderRadius: '50%', background: GOOD_COLOR }}></div>
            <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Good: 50K–150K views</span>
          </div>
          <div className="flex items-center gap-8">
            <div style={{ width: 10, height: 10, borderRadius: '50%', background: LOW_COLOR }}></div>
            <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Low: Under 50K views</span>
          </div>
        </div>
      </div>
    </div>
  );
}
