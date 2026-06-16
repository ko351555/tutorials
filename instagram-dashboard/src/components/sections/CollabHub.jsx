import { useState } from 'react';
import CopyButton from '../CopyButton';

const ACCOUNT = {
  handle: '@thecozyfamily.ai',
  name: 'The Cozy Family',
  niche: 'AI Animated Pixar Family | Baby, Dog & Cozy Lifestyle',
  followers: '2,975',
  views: '1.3M',
  bestReel: '557K',
  location: 'Glasgow, Scotland, UK',
  email: 'hello@thecozyfamily.ai',
  engRate: '12.8%',
};

function buildTemplate(brand, type) {
  const isAI = type === 'ai';
  const subject = isAI
    ? `Collaboration Opportunity — @thecozyfamily.ai × ${brand.name} 🤝`
    : `Brand Partnership Proposal — @thecozyfamily.ai (1.3M Views) 💛`;

  const body = isAI ? `Subject: ${subject}

Hi ${brand.name} Team,

I hope this message finds you well! I'm reaching out to explore a collaboration opportunity that I believe would be a great fit for ${brand.name}.

I'm the creator behind ${ACCOUNT.handle} — an AI-animated Pixar-style family account based in Glasgow, UK. We create heartfelt, cozy content featuring our family of four (mum, dad, baby, and our golden dog), all brought to life through AI animation.

📊 Our Stats at a Glance:
• Followers: ${ACCOUNT.followers} (growing daily)
• Total Views (30 days): ${ACCOUNT.views}
• Best Performing Reel: ${ACCOUNT.bestReel} views
• Avg Engagement Rate: ${ACCOUNT.engRate} (industry avg: 3-5%)
• Posting: Daily at 5:30am UK time
• Audience: Primarily parents, families, pet owners (UK & global)

🎬 Why ${brand.name} + The Cozy Family AI?

Your tool powers the very content our audience loves. A collaboration would be authentic, educational, and highly shareable — showing real creative results with ${brand.name}, not just a logo placement.

💡 What I'm Proposing:
• 1 dedicated reel showcasing ${brand.name} in our signature Pixar-style family format
• Behind-the-scenes process content (Stories + Reel)
• Genuine creative testimonial from a fast-growing AI creator

💰 Rate Card:
• Story Mention: £50
• Feed Post: £100–£150
• Dedicated Reel: £200–£300
• 3 Reel Package: £500

I'm open to discussing what works best for your campaign goals. I'd love to create something truly special together.

Would you be open to a quick call this week?

Warm regards,
${ACCOUNT.name}
${ACCOUNT.handle}
${ACCOUNT.email}
Glasgow, Scotland, UK`

  : `Subject: ${subject}

Hi ${brand.name} Team,

I'm reaching out on behalf of ${ACCOUNT.handle} — one of the UK's fastest-growing AI family content accounts on Instagram.

We create warm, Pixar-style animated family content featuring our cozy family of four: mum, dad, baby, and our beloved golden dog. Our content consistently resonates with parents, families, and lifestyle enthusiasts across the UK and globally.

📊 Account Highlights:
• Followers: ${ACCOUNT.followers} organic followers
• Total Views (30 days): ${ACCOUNT.views}
• Top Reel Performance: ${ACCOUNT.bestReel} views
• Average Engagement Rate: ${ACCOUNT.engRate} (4× industry average)
• Daily posting at 5:30am UK — peak scroll time
• Audience: Parents, new mums/dads, dog lovers, UK families

🎯 Why We're a Perfect Match for ${brand.name}:

Our audience are exactly your customers — young UK families who care about quality, comfort, and real family moments. Our authentic, emotional storytelling style makes brand integrations feel natural, not forced.

🎬 Collaboration Ideas:
• Feature ${brand.name} products in our golden home setting
• "Morning routine" reel with natural product placement
• "Best purchase for our family" authentic review format
• Giveaway collaboration to grow both audiences

💰 Transparent Rate Card:
• Story Mention: £50
• Feed Post: £100–£150
• Dedicated Reel: £200–£300
• 3 Reel Package: £500 (most popular)

I would love to send over our full Media Kit and discuss how we can create content that genuinely resonates with your audience.

Are you available for a quick call this week to explore possibilities?

With warm regards,
${ACCOUNT.name}
${ACCOUNT.handle}
${ACCOUNT.email}
Glasgow, Scotland, UK`;

  return { subject, body };
}

const aiBrands = [
  { name: 'Kling AI', focus: 'AI video generation platform', type: 'ai' },
  { name: 'Google Flow', focus: 'AI creative suite for video', type: 'ai' },
  { name: 'Higgsfield', focus: 'AI character animation tool', type: 'ai' },
  { name: 'CapCut', focus: 'Video editing & AI effects app', type: 'ai' },
  { name: 'Runway ML', focus: 'Professional AI video generation', type: 'ai' },
];

const familyBrands = [
  { name: 'Tommee Tippee', focus: 'Baby feeding & care products', type: 'family' },
  { name: 'Pampers UK', focus: 'Baby nappies & skincare', type: 'family' },
  { name: 'Boots Baby', focus: 'UK baby health & beauty', type: 'family' },
  { name: 'Dunelm', focus: 'Homeware & cosy living', type: 'family' },
  { name: 'Next UK', focus: 'Family fashion & home', type: 'family' },
  { name: 'Aldi Baby UK', focus: 'Value baby products', type: 'family' },
];

export default function CollabHub() {
  const [selectedBrand, setSelectedBrand] = useState(null);
  const [activeGroup, setActiveGroup] = useState('ai');

  const brands = activeGroup === 'ai' ? aiBrands : familyBrands;

  return (
    <div className="section-wrapper">
      <div className="section-header">
        <h1 className="section-title">🤝 Brand Collaboration Hub</h1>
        <p className="section-subtitle">Ready-to-send professional email templates for every brand partnership</p>
      </div>

      {/* Rate Card */}
      <div className="grid-2 mb-20">
        <div className="rate-card">
          <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--gold)', marginBottom: 14 }}>💰 Your Rate Card</div>
          {[
            { type: 'Story Mention', price: '£50' },
            { type: 'Feed Post', price: '£100–£150' },
            { type: 'Dedicated Reel', price: '£200–£300' },
            { type: '3 Reel Package ⭐', price: '£500' },
          ].map((r, i) => (
            <div key={i} className="rate-item">
              <span className="rate-label">{r.type}</span>
              <span className="rate-price">{r.price}</span>
            </div>
          ))}
        </div>

        <div className="card">
          <div className="card-title">📊 Pitch Stats (auto-filled in templates)</div>
          {[
            { label: 'Instagram Handle', value: ACCOUNT.handle },
            { label: 'Followers', value: ACCOUNT.followers },
            { label: 'Views (30 days)', value: ACCOUNT.views },
            { label: 'Best Reel', value: ACCOUNT.bestReel },
            { label: 'Engagement Rate', value: ACCOUNT.engRate },
            { label: 'Location', value: ACCOUNT.location },
          ].map((s, i) => (
            <div key={i} className="flex items-center justify-between" style={{ padding: '7px 0', borderBottom: '1px solid var(--border)', fontSize: 13 }}>
              <span style={{ color: 'var(--text-secondary)' }}>{s.label}</span>
              <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{s.value}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Brand selector */}
      <div className="tabs">
        <button className={`tab ${activeGroup === 'ai' ? 'active' : ''}`} onClick={() => { setActiveGroup('ai'); setSelectedBrand(null); }}>🤖 AI Tool Brands</button>
        <button className={`tab ${activeGroup === 'family' ? 'active' : ''}`} onClick={() => { setActiveGroup('family'); setSelectedBrand(null); }}>👶 Kids & Family Brands</button>
      </div>

      <div className="grid-2 mb-20">
        <div>
          <div className="card-title" style={{ marginBottom: 12, paddingLeft: 4 }}>
            {activeGroup === 'ai' ? '🤖 AI Tool Brands' : '👶 Kids & Family Brands'}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {brands.map((brand, i) => (
              <div
                key={i}
                onClick={() => setSelectedBrand(brand)}
                style={{
                  background: selectedBrand?.name === brand.name ? 'var(--gold-dim)' : 'var(--bg-card)',
                  border: `1px solid ${selectedBrand?.name === brand.name ? 'var(--gold-border)' : 'var(--border)'}`,
                  borderRadius: 10,
                  padding: '13px 15px',
                  cursor: 'pointer',
                  transition: 'all 0.15s',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <div>
                  <div style={{ fontSize: 14, fontWeight: 600, color: selectedBrand?.name === brand.name ? 'var(--gold)' : 'var(--text-primary)' }}>{brand.name}</div>
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>{brand.focus}</div>
                </div>
                <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>→</span>
              </div>
            ))}
          </div>
        </div>

        <div>
          {selectedBrand ? (() => {
            const { subject, body } = buildTemplate(selectedBrand, selectedBrand.type);
            return (
              <div className="card" style={{ height: '100%' }}>
                <div className="flex items-center justify-between mb-12">
                  <div style={{ fontSize: 14, fontWeight: 700 }}>✉️ {selectedBrand.name}</div>
                  <div className="flex gap-8">
                    <CopyButton text={subject} label="Subject" />
                    <CopyButton text={body} label="Full Email" />
                  </div>
                </div>

                <div style={{ marginBottom: 12 }}>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 6 }}>Subject Line</div>
                  <div style={{ background: 'var(--bg-card2)', border: '1px solid var(--border)', borderRadius: 8, padding: '10px 12px', fontSize: 13, color: 'var(--gold)', fontWeight: 500 }}>
                    {subject}
                  </div>
                </div>

                <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 6 }}>Email Body</div>
                <div className="email-template" style={{ maxHeight: 380, overflowY: 'auto', fontSize: 12.5 }}>{body}</div>

                <div className="template-actions">
                  <CopyButton text={body} label="Copy Full Email" />
                  <button
                    className="btn btn-outline btn-sm"
                    onClick={() => {
                      const ml = `mailto:partnerships@${selectedBrand.name.toLowerCase().replace(/\s/g, '')}.com?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
                      window.open(ml);
                    }}
                  >
                    📧 Open in Mail
                  </button>
                </div>
              </div>
            );
          })() : (
            <div className="card" style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 12, color: 'var(--text-muted)' }}>
              <div style={{ fontSize: 48 }}>👆</div>
              <div style={{ fontSize: 14 }}>Select a brand to see your template</div>
            </div>
          )}
        </div>
      </div>

      {/* Outreach tips */}
      <div className="card">
        <div className="card-title">🎯 Outreach Strategy Tips</div>
        <div className="grid-3">
          {[
            { icon: '🔍', title: 'Find Contact', tip: 'Search LinkedIn for "Influencer Manager" or "Brand Partnerships" at each company. DM on Instagram as backup.' },
            { icon: '⏰', title: 'Best Send Time', tip: 'Tuesday–Thursday, 9–11am. Avoid Mondays (inbox chaos) and Fridays (weekend mode).' },
            { icon: '📊', title: 'Lead with Stats', tip: 'Your 1.3M views and 12.8% engagement rate are exceptional. Lead with those, not follower count.' },
            { icon: '🎬', title: 'Include Video Link', tip: 'Attach your 557K view reel. Seeing is believing. Link your best performing content first.' },
            { icon: '🔄', title: 'Follow Up Once', tip: 'Wait 5 business days then send one polite follow-up. No more than 2 total contacts.' },
            { icon: '💼', title: 'Track Responses', tip: 'Log every outreach in the Monetization Tracker → Brand Deals section below.' },
          ].map((t, i) => (
            <div key={i} style={{ background: 'var(--bg-card2)', borderRadius: 8, padding: '13px 15px', border: '1px solid var(--border)' }}>
              <div style={{ fontSize: 18, marginBottom: 7 }}>{t.icon}</div>
              <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4 }}>{t.title}</div>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.5 }}>{t.tip}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
