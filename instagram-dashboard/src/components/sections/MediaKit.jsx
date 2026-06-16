import { useState } from 'react';
import { useLocalStorage } from '../../hooks/useLocalStorage';

const defaultStats = {
  handle: '@thecozyfamily.ai',
  name: 'The Cozy Family AI',
  tagline: 'AI Animated Pixar Family | Baby · Dog · Cozy Lifestyle',
  followers: '2,975',
  views30d: '1.3M',
  bestReel: '557K',
  engRate: '12.8',
  postingTime: '5:30am UK daily',
  niche: 'AI Family Content · Baby · Dog · Parents · Cozy Lifestyle',
  location: 'Glasgow, Scotland, UK',
  email: 'hello@thecozyfamily.ai',
  audienceAge: '25–34 (62%)',
  audienceGender: 'Female 68% / Male 32%',
  audienceTop: 'UK (58%) · Ireland (12%) · USA (18%)',
};

export default function MediaKit() {
  const [stats, setStats] = useLocalStorage('mediakit_stats', defaultStats);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(stats);

  const save = () => { setStats(draft); setEditing(false); };

  const Field = ({ label, k, w = '1' }) => (
    <div className="form-group" style={{ marginBottom: 0, gridColumn: `span ${w}` }}>
      <label>{label}</label>
      <input value={draft[k]} onChange={e => setDraft({ ...draft, [k]: e.target.value })} />
    </div>
  );

  const handlePrint = () => window.print();

  return (
    <div className="section-wrapper">
      <div className="section-header">
        <h1 className="section-title">📄 Media Kit Generator</h1>
        <p className="section-subtitle">Professional media kit auto-filled from your stats — edit and export</p>
      </div>

      <div className="flex items-center justify-between mb-20" style={{ flexWrap: 'wrap', gap: 10 }}>
        <div className="flex gap-8">
          <button className="btn btn-outline" onClick={() => { setDraft(stats); setEditing(!editing); }}>
            {editing ? '✕ Cancel' : '✏️ Edit Stats'}
          </button>
          {editing && <button className="btn btn-gold" onClick={save}>💾 Save</button>}
        </div>
        <button className="btn btn-gold" onClick={handlePrint}>
          📥 Download / Print PDF
        </button>
      </div>

      {editing && (
        <div className="card mb-20">
          <div className="card-title">✏️ Edit Your Stats</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
            <Field label="Handle" k="handle" />
            <Field label="Display Name" k="name" />
            <Field label="Tagline" k="tagline" w="2" />
            <Field label="Followers" k="followers" />
            <Field label="Views (30d)" k="views30d" />
            <Field label="Best Reel Views" k="bestReel" />
            <Field label="Engagement Rate (%)" k="engRate" />
            <Field label="Posting Schedule" k="postingTime" />
            <Field label="Niche" k="niche" w="2" />
            <Field label="Location" k="location" />
            <Field label="Contact Email" k="email" />
            <Field label="Audience Age" k="audienceAge" />
            <Field label="Audience Gender" k="audienceGender" />
            <Field label="Top Countries" k="audienceTop" w="2" />
          </div>
        </div>
      )}

      {/* Media Kit Preview */}
      <div className="media-kit" id="media-kit-print">
        {/* Header */}
        <div className="media-kit-header">
          <div className="media-kit-avatar">🏠</div>
          <div className="media-kit-name">{stats.name}</div>
          <div className="media-kit-handle">{stats.handle} · {stats.location}</div>
          <div className="media-kit-desc">{stats.tagline}</div>
        </div>

        {/* Body */}
        <div className="media-kit-body">
          {/* Key Stats */}
          <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: 12 }}>
            📊 Key Statistics
          </div>
          <div className="kit-stats-grid mb-20">
            {[
              { label: 'Followers', value: stats.followers },
              { label: '30-Day Views', value: stats.views30d },
              { label: 'Best Reel', value: stats.bestReel },
              { label: 'Engagement Rate', value: stats.engRate + '%' },
            ].map((s, i) => (
              <div key={i} className="kit-stat">
                <div className="kit-stat-value">{s.value}</div>
                <div className="kit-stat-label">{s.label}</div>
              </div>
            ))}
          </div>

          {/* Audience & Content */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 24 }}>
            <div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: 12 }}>👥 Audience Demographics</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {[
                  { label: 'Primary Age', value: stats.audienceAge },
                  { label: 'Gender Split', value: stats.audienceGender },
                  { label: 'Top Locations', value: stats.audienceTop },
                  { label: 'Posting Time', value: stats.postingTime },
                ].map((d, i) => (
                  <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '7px 0', borderBottom: '1px solid var(--border)', fontSize: 13 }}>
                    <span style={{ color: 'var(--text-secondary)' }}>{d.label}</span>
                    <span style={{ fontWeight: 600, textAlign: 'right', maxWidth: '55%' }}>{d.value}</span>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: 12 }}>🎬 Content Style</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
                {[
                  '🤖 AI-generated Pixar-style family animation',
                  '👶 Baby, dog & cozy family moments',
                  '🏠 Golden bedroom & kitchen aesthetic',
                  '❤️ Emotional first-person storytelling',
                  '🎬 Short punchy reels (15–30 seconds)',
                  '📅 Posted daily at 5:30am UK time',
                ].map((item, i) => (
                  <div key={i} style={{ fontSize: 13, color: 'var(--text-secondary)', display: 'flex', gap: 6 }}>
                    <span>{item}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Content examples placeholder */}
          <div style={{ marginBottom: 24 }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: 12 }}>🖼️ Top Performing Content</div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
              {[
                { title: 'Baby & Dog Morning Cuddle', views: '557K views 🔥', type: 'Reel' },
                { title: 'First Steps Moment', views: '218K views ⭐', type: 'Reel' },
                { title: 'Sunday Family Pancakes', views: '145K views ⭐', type: 'Reel' },
              ].map((c, i) => (
                <div key={i} style={{
                  background: 'var(--bg-card2)',
                  border: '1px solid var(--border)',
                  borderRadius: 10,
                  padding: '14px',
                  textAlign: 'center'
                }}>
                  <div style={{ fontSize: 32, marginBottom: 8 }}>{['🏆', '🥈', '🥉'][i]}</div>
                  <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 4 }}>{c.title}</div>
                  <div style={{ fontSize: 11, color: 'var(--gold)' }}>{c.views}</div>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 3 }}>{c.type}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Rate Card */}
          <div style={{ marginBottom: 24 }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: 12 }}>💰 Rate Card</div>
            <div style={{ background: 'linear-gradient(135deg, rgba(245,166,35,0.08), transparent)', border: '1px solid var(--gold-border)', borderRadius: 12, padding: '16px 20px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
                {[
                  { type: 'Story Mention', price: '£50' },
                  { type: 'Feed Post', price: '£100–£150' },
                  { type: 'Dedicated Reel', price: '£200–£300' },
                  { type: '3 Reel Package', price: '£500 ⭐' },
                ].map((r, i) => (
                  <div key={i} style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 16, fontWeight: 800, color: 'var(--gold)' }}>{r.price}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 3 }}>{r.type}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Partnership examples */}
          <div style={{ marginBottom: 24 }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: 12 }}>🤝 Ideal Partnership Fit</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {['AI Tool Brands', 'Baby Products', 'Family Lifestyle', 'Pet Brands', 'UK Home Brands', 'Parenting Apps', 'Cozy Home', 'Scottish Brands'].map((tag, i) => (
                <span key={i} style={{ background: 'var(--bg-card2)', border: '1px solid var(--border)', borderRadius: 20, padding: '4px 12px', fontSize: 12, color: 'var(--text-secondary)' }}>{tag}</span>
              ))}
            </div>
          </div>

          {/* Contact */}
          <div style={{ background: 'var(--bg-card2)', borderRadius: 12, padding: '18px 20px', border: '1px solid var(--border)' }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: 10 }}>📬 Get in Touch</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16 }}>
              <div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 3 }}>EMAIL</div>
                <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--gold)' }}>{stats.email}</div>
              </div>
              <div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 3 }}>INSTAGRAM</div>
                <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--gold)' }}>{stats.handle}</div>
              </div>
              <div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 3 }}>LOCATION</div>
                <div style={{ fontSize: 13, fontWeight: 600 }}>{stats.location}</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <style>{`
        @media print {
          .sidebar, .mobile-toggle, .sidebar-overlay { display: none !important; }
          .main-content { margin-left: 0 !important; }
          .section-header, .flex.items-center.justify-between { display: none !important; }
          #media-kit-print { border: none !important; }
          body { background: white !important; }
          .media-kit-header { background: #1a1200 !important; }
        }
      `}</style>
    </div>
  );
}
