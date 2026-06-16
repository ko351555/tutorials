import { useState } from 'react';
import { useLocalStorage } from '../../hooks/useLocalStorage';

const defaultDeals = [
  { id: 1, brand: 'Example Brand', type: 'Reel', value: 250, status: 'Prospect', date: '2026-06-16', notes: 'Initial email sent' },
];

const defaultOrders = [
  { id: 1, client: 'Sarah M.', type: 'Premium Portrait', value: 35, status: 'Complete', date: '2026-06-10' },
];

const REVENUE_STREAMS = [
  {
    icon: '🤝',
    title: 'Brand Collaborations',
    potential: '£200–£1,500/month',
    color: '#F5A623',
    steps: [
      'Build your Media Kit (Section 5 — done! ✅)',
      'Identify 5 brands per week using the Collab Hub',
      'Send personalised email (templates ready in Section 3)',
      'Follow up once after 5 business days',
      'Negotiate: story £50 → reel £200–£300 → package £500',
      'Track all deals in the Deal Tracker below',
    ],
    tips: 'At 2,975 followers + 1.3M views, you\'re already pitchable. Lead with your views and 12.8% engagement, not follower count.',
  },
  {
    icon: '🎨',
    title: 'Portrait Service',
    potential: '£200–£600/month',
    color: '#A855F7',
    steps: [
      'Current: Basic £20 / Premium £35 — consider raising to £25/£45 at 3K followers',
      'Add "Rush Order" tier: £50 for 24hr turnaround',
      'Add "Family Scene Pack": 3 scenes for £89',
      'Sell via Instagram DM + link in bio (Stan Store or Linktree)',
      'Create a pinned highlight "Order a Portrait 🎨"',
      'Post a "portrait reveal" reel weekly — drives new orders',
    ],
    tips: 'Showcase 3–4 completed portraits in a weekly reel. Customer reveal posts perform extremely well for this niche.',
  },
  {
    icon: '📦',
    title: 'Digital Products',
    potential: '£150–£500/month',
    color: '#22C55E',
    steps: [
      'Create "AI Family Portrait Prompt Pack" (50 prompts) — sell at £9.99',
      'Create "Cozy Home Scene Prompts" (30 prompts) — sell at £7.99',
      'Bundle both as "The Cozy Creator Pack" — £14.99',
      'List on Etsy (search traffic) + Gumroad (no fees on first £100)',
      'Promote in Stories weekly with link sticker',
      'Update pack every month → repeat purchases',
    ],
    tips: 'Your audience specifically wants AI prompts! You have a unique advantage — you live this niche daily.',
  },
  {
    icon: '🔗',
    title: 'Affiliate Marketing',
    potential: '£50–£300/month',
    color: '#60A5FA',
    steps: [
      'Sign up for Amazon UK Associates (promote baby/dog/home products)',
      'Join Kling AI affiliate program (direct link in bio)',
      'Apply to Awin (UK\'s biggest affiliate network — has Dunelm, Next, Boots)',
      'Add affiliate links via Linktree or Stan Store',
      'Mention products naturally in captions + Stories',
      'Track clicks in each program\'s dashboard',
    ],
    tips: 'Recommend products you already use in your videos. Authenticity drives clicks. Baby and dog products convert very well.',
  },
  {
    icon: '📺',
    title: 'YouTube Channel',
    potential: '£100–£800/month (6–12 months)',
    color: '#EF4444',
    steps: [
      'Start "The Cozy Family AI — Behind the Magic" YouTube channel',
      'Repurpose best Instagram reels as YouTube Shorts (1min) weekly',
      'Add "How I made this AI video" long-form monthly (10–15min)',
      'Requirements: 1,000 subscribers + 4,000 watch hours for monetisation',
      'Expected timeline: 6–12 months at current growth rate',
      'YouTube Shorts can drive Instagram followers back and vice versa',
    ],
    tips: 'Cross-posting to YouTube Shorts requires zero extra work. Upload the same reel there daily for free follower growth.',
  },
  {
    icon: '🏆',
    title: 'Patreon / Membership',
    potential: '£150–£600/month',
    color: '#EAB308',
    steps: [
      'Launch at 5K followers — timed with your next milestone',
      'Tier 1 "Cozy Insider" £3/month: Early access to reels + bloopers',
      'Tier 2 "Family Friend" £8/month: Monthly AI tutorial + prompt pack',
      'Tier 3 "Founding Member" £15/month: All above + 1 personal portrait/month',
      'Use Patreon\'s free plan until you hit £100/month',
      'Promote with a reel: "Join our cozy inner circle ❤️"',
    ],
    tips: 'Even 50 members at £5/month = £250 reliable monthly income. Focus on the community feel, not the money ask.',
  },
  {
    icon: '🎛️',
    title: 'Presets & Templates',
    potential: '£80–£250/month',
    color: '#F97316',
    steps: [
      'Create "Cozy Golden Hour" CapCut template pack — £5.99',
      'Create "AI Family Story" Instagram template set (Canva) — £7.99',
      'Create "Cozy Reel Captions" swipe file (50 captions) — £4.99',
      'Sell on Etsy, Gumroad, or your Stan Store',
      'Bundle as "The Cozy Creator Bundle" for £14.99',
      'Post a reel using the template — "Template in my bio" in caption',
    ],
    tips: 'Templates and caption packs require one-time creation effort but sell passively for months. Start with one product.',
  },
];

const affiliates = [
  { name: 'Amazon UK Associates', desc: 'Baby, dog & home products', rate: '3–10%', est: '£20–80/mo' },
  { name: 'Kling AI Affiliate', desc: 'AI video tool for creators', rate: '20–30%', est: '£30–120/mo' },
  { name: 'CapCut Affiliate', desc: 'Video editing app referrals', rate: '£5–15/ref', est: '£20–60/mo' },
  { name: 'Awin (UK Network)', desc: 'Dunelm, Next, Boots Baby etc', rate: '5–15%', est: '£40–150/mo' },
  { name: 'Etsy Affiliate', desc: 'Baby & home products', rate: '4%', est: '£15–40/mo' },
  { name: 'Gumroad Referral', desc: 'Digital products platform', rate: '10%', est: '£10–30/mo' },
];

export default function MonetizationTracker() {
  const [deals, setDeals] = useLocalStorage('deals', defaultDeals);
  const [orders, setOrders] = useLocalStorage('orders', defaultOrders);
  const [activeTab, setActiveTab] = useState('streams');
  const [expandedCard, setExpandedCard] = useState(null);
  const [newDeal, setNewDeal] = useState({ brand: '', type: 'Reel', value: '', status: 'Prospect', date: '', notes: '' });
  const [newOrder, setNewOrder] = useState({ client: '', type: 'Basic Portrait', value: '', status: 'Pending', date: '' });
  const [showDealForm, setShowDealForm] = useState(false);
  const [showOrderForm, setShowOrderForm] = useState(false);

  const dealRevenue = deals.filter(d => d.status === 'Paid').reduce((s, d) => s + +d.value, 0);
  const orderRevenue = orders.filter(o => o.status === 'Complete').reduce((s, o) => s + +o.value, 0);
  const totalRevenue = dealRevenue + orderRevenue;

  const addDeal = () => {
    if (!newDeal.brand) return;
    setDeals([{ ...newDeal, id: Date.now(), value: +newDeal.value }, ...deals]);
    setNewDeal({ brand: '', type: 'Reel', value: '', status: 'Prospect', date: '', notes: '' });
    setShowDealForm(false);
  };

  const addOrder = () => {
    if (!newOrder.client) return;
    setOrders([{ ...newOrder, id: Date.now(), value: +newOrder.value }, ...orders]);
    setNewOrder({ client: '', type: 'Basic Portrait', value: '', status: 'Pending', date: '' });
    setShowOrderForm(false);
  };

  const statusColor = { Prospect: 'badge-blue', 'In Talks': 'badge-yellow', Confirmed: 'badge-gold', Paid: 'badge-green', Rejected: 'badge-red' };
  const orderStatusColor = { Pending: 'badge-yellow', 'In Progress': 'badge-blue', Complete: 'badge-green', Cancelled: 'badge-red' };

  return (
    <div className="section-wrapper">
      <div className="section-header">
        <h1 className="section-title">💰 Monetization Tracker</h1>
        <p className="section-subtitle">Every revenue stream · Step-by-step guide · Track deals & orders</p>
      </div>

      {/* Revenue summary */}
      <div className="grid-4 mb-20">
        <div className="metric-card">
          <div className="metric-icon">🤝</div>
          <div className="metric-value">£{dealRevenue}</div>
          <div className="metric-label">Brand Deal Revenue</div>
        </div>
        <div className="metric-card">
          <div className="metric-icon">🎨</div>
          <div className="metric-value">£{orderRevenue}</div>
          <div className="metric-label">Portrait Orders</div>
        </div>
        <div className="metric-card">
          <div className="metric-icon">💎</div>
          <div className="metric-value">£{totalRevenue}</div>
          <div className="metric-label">Total Earned</div>
        </div>
        <div className="metric-card">
          <div className="metric-icon">🎯</div>
          <div className="metric-value">£{(2750 - totalRevenue).toLocaleString()}</div>
          <div className="metric-label">To £2,750 Goal</div>
        </div>
      </div>

      <div className="tabs">
        {[['streams', '💡 Revenue Streams'], ['deals', '🤝 Deal Tracker'], ['portraits', '🎨 Portrait Orders'], ['affiliates', '🔗 Affiliates']].map(([k, l]) => (
          <button key={k} className={`tab ${activeTab === k ? 'active' : ''}`} onClick={() => setActiveTab(k)}>{l}</button>
        ))}
      </div>

      {activeTab === 'streams' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {REVENUE_STREAMS.map((stream, i) => (
            <div key={i} className="money-card">
              <div className="money-card-header" onClick={() => setExpandedCard(expandedCard === i ? null : i)} style={{ cursor: 'pointer' }}>
                <div className="money-icon">{stream.icon}</div>
                <div style={{ flex: 1 }}>
                  <div className="money-title">{stream.title}</div>
                  <div className="money-potential">{stream.potential}</div>
                </div>
                <span style={{ color: 'var(--text-muted)', fontSize: 18 }}>{expandedCard === i ? '▲' : '▼'}</span>
              </div>
              {expandedCard === i && (
                <div className="money-card-body">
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
                    <div>
                      <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 10 }}>Steps</div>
                      <div className="step-list">
                        {stream.steps.map((step, j) => (
                          <div key={j} className="step-item">
                            <div className="step-num">{j + 1}</div>
                            <div className="step-text">{step}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 10 }}>💡 Pro Tip</div>
                      <div style={{ background: 'var(--bg-card2)', border: '1px solid var(--border)', borderRadius: 8, padding: '14px', fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                        {stream.tips}
                      </div>
                      <div style={{ marginTop: 14, background: 'var(--gold-dim)', border: '1px solid var(--gold-border)', borderRadius: 8, padding: '10px 14px' }}>
                        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>INCOME POTENTIAL</div>
                        <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--gold)' }}>{stream.potential}</div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {activeTab === 'deals' && (
        <div className="card">
          <div className="flex items-center justify-between mb-16">
            <div className="card-title" style={{ marginBottom: 0 }}>🤝 Brand Deal Tracker</div>
            <button className="btn btn-gold btn-sm" onClick={() => setShowDealForm(!showDealForm)}>
              {showDealForm ? '✕ Cancel' : '＋ Add Deal'}
            </button>
          </div>

          {showDealForm && (
            <div style={{ background: 'var(--bg-card2)', borderRadius: 10, padding: 16, marginBottom: 16, border: '1px solid var(--border)' }}>
              <div className="form-row mb-12">
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label>Brand Name</label>
                  <input placeholder="e.g. Kling AI" value={newDeal.brand} onChange={e => setNewDeal({ ...newDeal, brand: e.target.value })} />
                </div>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label>Deal Type</label>
                  <select value={newDeal.type} onChange={e => setNewDeal({ ...newDeal, type: e.target.value })}>
                    <option>Story Mention</option><option>Feed Post</option><option>Reel</option><option>3 Reel Package</option>
                  </select>
                </div>
              </div>
              <div className="form-row mb-12">
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label>Value (£)</label>
                  <input type="number" placeholder="250" value={newDeal.value} onChange={e => setNewDeal({ ...newDeal, value: e.target.value })} />
                </div>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label>Status</label>
                  <select value={newDeal.status} onChange={e => setNewDeal({ ...newDeal, status: e.target.value })}>
                    <option>Prospect</option><option>In Talks</option><option>Confirmed</option><option>Paid</option><option>Rejected</option>
                  </select>
                </div>
              </div>
              <div className="form-group mb-12">
                <label>Notes</label>
                <input placeholder="e.g. Emailed 16 June, waiting for reply" value={newDeal.notes} onChange={e => setNewDeal({ ...newDeal, notes: e.target.value })} />
              </div>
              <button className="btn btn-gold btn-sm" onClick={addDeal}>Save Deal</button>
            </div>
          )}

          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Brand</th><th>Type</th><th>Value</th><th>Status</th><th>Notes</th><th></th>
                </tr>
              </thead>
              <tbody>
                {deals.map(deal => (
                  <tr key={deal.id}>
                    <td style={{ fontWeight: 600 }}>{deal.brand}</td>
                    <td><span className="badge badge-blue">{deal.type}</span></td>
                    <td style={{ fontWeight: 700, color: 'var(--gold)' }}>£{deal.value}</td>
                    <td><span className={`badge ${statusColor[deal.status] || 'badge-blue'}`}>{deal.status}</span></td>
                    <td style={{ color: 'var(--text-secondary)', fontSize: 12 }}>{deal.notes}</td>
                    <td>
                      <button onClick={() => setDeals(deals.filter(d => d.id !== deal.id))} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>✕</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'portraits' && (
        <div className="card">
          <div className="flex items-center justify-between mb-16">
            <div className="card-title" style={{ marginBottom: 0 }}>🎨 Portrait Order Tracker</div>
            <button className="btn btn-gold btn-sm" onClick={() => setShowOrderForm(!showOrderForm)}>
              {showOrderForm ? '✕ Cancel' : '＋ Add Order'}
            </button>
          </div>

          <div className="grid-3 mb-16">
            {[
              { tier: 'Basic Portrait', price: '£20', desc: '1 scene, standard render, 48hr delivery' },
              { tier: 'Premium Portrait', price: '£35', desc: '2 scenes, HD render, 24hr delivery + revisions' },
              { tier: 'Rush Order', price: '£50', desc: '1 scene, 6hr turnaround (add-on to any tier)' },
            ].map((t, i) => (
              <div key={i} style={{ background: 'var(--bg-card2)', border: '1px solid var(--border)', borderRadius: 10, padding: '14px 16px' }}>
                <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--gold)', marginBottom: 3 }}>{t.tier}</div>
                <div style={{ fontSize: 20, fontWeight: 800, color: 'var(--text-primary)', marginBottom: 6 }}>{t.price}</div>
                <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{t.desc}</div>
              </div>
            ))}
          </div>

          {showOrderForm && (
            <div style={{ background: 'var(--bg-card2)', borderRadius: 10, padding: 16, marginBottom: 16, border: '1px solid var(--border)' }}>
              <div className="form-row mb-12">
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label>Client Name</label>
                  <input placeholder="e.g. Sarah M." value={newOrder.client} onChange={e => setNewOrder({ ...newOrder, client: e.target.value })} />
                </div>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label>Order Type</label>
                  <select value={newOrder.type} onChange={e => setNewOrder({ ...newOrder, type: e.target.value })}>
                    <option>Basic Portrait</option><option>Premium Portrait</option><option>Rush Order</option><option>Family Scene Pack</option>
                  </select>
                </div>
              </div>
              <div className="form-row mb-12">
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label>Value (£)</label>
                  <input type="number" placeholder="35" value={newOrder.value} onChange={e => setNewOrder({ ...newOrder, value: e.target.value })} />
                </div>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label>Status</label>
                  <select value={newOrder.status} onChange={e => setNewOrder({ ...newOrder, status: e.target.value })}>
                    <option>Pending</option><option>In Progress</option><option>Complete</option><option>Cancelled</option>
                  </select>
                </div>
              </div>
              <button className="btn btn-gold btn-sm" onClick={addOrder}>Save Order</button>
            </div>
          )}

          <div className="table-wrapper">
            <table>
              <thead>
                <tr><th>Client</th><th>Type</th><th>Value</th><th>Status</th><th></th></tr>
              </thead>
              <tbody>
                {orders.map(order => (
                  <tr key={order.id}>
                    <td style={{ fontWeight: 600 }}>{order.client}</td>
                    <td><span className="badge badge-purple">{order.type}</span></td>
                    <td style={{ fontWeight: 700, color: 'var(--gold)' }}>£{order.value}</td>
                    <td><span className={`badge ${orderStatusColor[order.status] || 'badge-blue'}`}>{order.status}</span></td>
                    <td>
                      <button onClick={() => setOrders(orders.filter(o => o.id !== order.id))} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>✕</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'affiliates' && (
        <div>
          <div className="card mb-16">
            <div className="card-title">🔗 Best Affiliate Programs for Your Niche</div>
            {affiliates.map((a, i) => (
              <div key={i} className="affiliate-item" style={{ marginBottom: i < affiliates.length - 1 ? 8 : 0 }}>
                <div>
                  <div className="affiliate-name">{a.name}</div>
                  <div className="affiliate-desc">{a.desc}</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div className="affiliate-rate">↑ {a.rate}</div>
                  <div className="affiliate-est">Est. {a.est}</div>
                </div>
              </div>
            ))}
          </div>

          <div className="card">
            <div className="card-title">📋 How to Add Affiliate Links</div>
            <div className="grid-2">
              <div className="step-list">
                {[
                  'Sign up for each affiliate program (links in their websites)',
                  'Get your unique tracking link for each product',
                  'Add top links to your Linktree or Stan Store',
                  'Mention products naturally in captions ("Amazon link in bio")',
                  'Add link sticker in Stories when you mention a product',
                  'Check your dashboard weekly for clicks + earnings',
                ].map((step, i) => (
                  <div key={i} className="step-item">
                    <div className="step-num">{i + 1}</div>
                    <div className="step-text">{step}</div>
                  </div>
                ))}
              </div>
              <div>
                <div style={{ background: 'var(--gold-dim)', border: '1px solid var(--gold-border)', borderRadius: 10, padding: '16px' }}>
                  <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--gold)', marginBottom: 10 }}>💡 Estimated Monthly Earnings</div>
                  {[
                    { program: 'Amazon UK', est: '£20–80' },
                    { program: 'Kling AI', est: '£30–120' },
                    { program: 'Awin Network', est: '£40–150' },
                    { program: 'CapCut', est: '£15–50' },
                  ].map((e, i) => (
                    <div key={i} className="flex items-center justify-between" style={{ padding: '6px 0', borderBottom: '1px solid rgba(245,166,35,0.2)', fontSize: 13 }}>
                      <span style={{ color: 'var(--text-secondary)' }}>{e.program}</span>
                      <span style={{ fontWeight: 600, color: 'var(--gold)' }}>{e.est}</span>
                    </div>
                  ))}
                  <div className="flex items-center justify-between mt-8" style={{ fontSize: 14 }}>
                    <span style={{ fontWeight: 600 }}>Total Potential</span>
                    <span style={{ fontWeight: 800, color: 'var(--gold)', fontSize: 16 }}>£105–400/mo</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
