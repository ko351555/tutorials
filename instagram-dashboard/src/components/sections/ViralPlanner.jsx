import { useState } from 'react';
import CopyButton from '../CopyButton';

const today = new Date();
const days = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];

function getDay(offset) {
  const d = new Date(today);
  d.setDate(d.getDate() + offset);
  return {
    name: days[d.getDay()],
    date: `${d.getDate()} ${months[d.getMonth()]}`,
  };
}

const calendar = [
  {
    offset: 0,
    idea: '🐶 Dog wakes baby with kisses — "He always knows"',
    caption: `He knew before I did.\n\nEvery morning, without fail.\nOur golden alarm clock.\n\n❤️ Save if this is your family too`,
    hashtags: '#AIFamily #BabyAndDog #CozyfamilyAI #FamilyMoments #DogAndBaby #PixarLife #GoldenHour',
    type: 'Reel', viralScore: 5,
  },
  {
    offset: 1,
    idea: '👶 Baby reaches for dad — first-person "I froze"',
    caption: `I froze.\n\nShe reached out her tiny hand.\nAnd chose me.\n\nI will never take this for granted 🤍`,
    hashtags: '#NewDad #BabyMoments #AIFamily #FamilyFirst #CozyfamilyAI #PixarFamily',
    type: 'Reel', viralScore: 5,
  },
  {
    offset: 2,
    idea: '🍳 Family breakfast — golden kitchen, all 4 members',
    caption: `This is my everything.\n\nChaos, syrup, tiny hands.\nAnd one very hopeful dog.\n\n🧇 Sunday mornings hit different`,
    hashtags: '#FamilyBreakfast #SundayVibes #AIFamily #CozyfamilyAI #FamilyLife #HomeMoments',
    type: 'Reel', viralScore: 4,
  },
  {
    offset: 3,
    idea: '🌅 Mum & baby morning light — bedroom golden hour',
    caption: `She fell asleep on my chest.\n\nI didn't move for an hour.\n\nSome moments are too precious to rush 🌅`,
    hashtags: '#MumLife #BabyNap #GoldenHour #AIFamily #CozyfamilyAI #MotherhoodUnfiltered',
    type: 'Reel', viralScore: 5,
  },
  {
    offset: 4,
    idea: '🐾 Dog guards sleeping baby — loyalty moment',
    caption: `He chose his human.\n\nNobody told him to stay.\nHe just knew.\n\n🐶 Dogs really are magic`,
    hashtags: '#DogLoyalty #BabyProtector #AIFamily #DogAndBaby #CozyfamilyAI #FurBaby',
    type: 'Reel', viralScore: 5,
  },
  {
    offset: 5,
    idea: '👨‍👩‍👧 Family dance in kitchen — playful energy',
    caption: `We don't need a reason.\n\nJust music, tiny feet, and him.\nThis is how we do Fridays 💃`,
    hashtags: '#FamilyDance #FridayFeeling #AIFamily #CozyfamilyAI #FamilyMoments #KitchenDance',
    type: 'Reel', viralScore: 4,
  },
  {
    offset: 6,
    idea: '❤️ Baby gives dog a hug — pure love',
    caption: `She learned love from him.\n\nNo one taught her.\nShe just wrapped her arms around him.\n\nAnd we all melted 🤍`,
    hashtags: '#BabyAndDog #PureLove #AIFamily #WeekendVibes #CozyfamilyAI #HeartMelting',
    type: 'Reel', viralScore: 5,
  },
];

const captionFormulas = [
  {
    name: '🔥 The Freeze Formula',
    template: 'I froze.\n\n[WHAT HAPPENED IN 1 LINE]\n\n[EMOTIONAL MEANING IN 1 LINE]\n\n[CALL TO FEELING — emoji + save ask]',
    example: 'I froze.\n\nShe said "dada" for the first time.\n\nI didn\'t expect it to hit that hard.\n\n🤍 Save this if you know the feeling',
    viralScore: 95,
  },
  {
    name: '💛 The Nobody Told Them Formula',
    template: 'Nobody told [PERSON/PET] to [ACTION].\n\nThey just knew.\n\n[EMOTIONAL 1-LINER]\n\n[emoji + community ask]',
    example: 'Nobody told him to stay.\n\nHe just lay beside her all night.\n\nDogs really do choose their humans.\n\n🐶 Share if your dog does this too',
    viralScore: 92,
  },
  {
    name: '⏰ The I Didn\'t Move Formula',
    template: 'I didn\'t move for [TIME].\n\n[REASON WHY]\n\n[WHAT IT MEANS TO YOU]\n\n[Soft CTA]',
    example: 'I didn\'t move for an hour.\n\nShe was asleep on my chest.\n\nSome moments are worth the pins and needles.\n\n❤️ Mums — you know this',
    viralScore: 90,
  },
  {
    name: '🌟 The This Is My Everything Formula',
    template: 'This is my everything.\n\n[LIST 3 chaotic/cozy things in 3 words max each]\n\n[Warm closing line]\n\n[emoji]',
    example: 'This is my everything.\n\nChaos, laughter, crumbs.\nOne dog who steals chips.\nAnd the best Sunday mornings.\n\n🧡 Same?',
    viralScore: 88,
  },
];

const hashtagSets = [
  {
    name: '🔥 Viral Baby + Dog',
    tags: '#AIFamily #BabyAndDog #CozyfamilyAI #FamilyMoments #DogAndBaby #PixarLife #NewParent #BabyLove #FurBaby #GoldenHour #FamilyGoals #InstaBaby',
    use: 'When dog & baby are both in frame',
  },
  {
    name: '💛 Emotional / Narrative',
    tags: '#MumLife #DadLife #ParentingMoments #FamilyFirst #CozyfamilyAI #AIFamily #BabyMilestones #ParentingLife #FamilyVibes #RealParenting',
    use: 'For emotional first-person reels',
  },
  {
    name: '🏠 Cozy Home / Lifestyle',
    tags: '#CosyHome #CozyLife #HomeVibes #GoldenHour #HomeAesthetic #FamilyHome #CozyfamilyAI #AIFamily #InteriorVibes #HomeGoals #CozyLiving',
    use: 'For golden bedroom / kitchen content',
  },
  {
    name: '🤖 AI Content Creator',
    tags: '#AIArt #AIAnimation #PixarStyle #AIFamily #AICreator #AIContent #AnimationArt #DigitalFamily #ContentCreator #AIGenerated #CozyfamilyAI',
    use: 'When highlighting the AI angle',
  },
];

export default function ViralPlanner() {
  const [activeTab, setActiveTab] = useState('calendar');
  const [copiedCap, setCopiedCap] = useState(null);
  const [copiedHash, setCopiedHash] = useState(null);

  const copy = (text, type, id) => {
    navigator.clipboard.writeText(text);
    if (type === 'cap') { setCopiedCap(id); setTimeout(() => setCopiedCap(null), 2000); }
    if (type === 'hash') { setCopiedHash(id); setTimeout(() => setCopiedHash(null), 2000); }
  };

  return (
    <div className="section-wrapper">
      <div className="section-header">
        <h1 className="section-title">🚀 Viral Content Planner</h1>
        <p className="section-subtitle">7-day content calendar · Proven caption formulas · Power hashtags · Ranked by viral potential</p>
      </div>

      <div className="tabs">
        {[['calendar','📅 7-Day Calendar'], ['captions','✍️ Caption Formulas'], ['hashtags','#️⃣ Hashtag Sets']].map(([k, l]) => (
          <button key={k} className={`tab ${activeTab === k ? 'active' : ''}`} onClick={() => setActiveTab(k)}>{l}</button>
        ))}
      </div>

      {activeTab === 'calendar' && (
        <>
          <div style={{ background: 'var(--gold-dim)', border: '1px solid var(--gold-border)', borderRadius: 10, padding: '10px 16px', marginBottom: 20, fontSize: 13, color: 'var(--gold)' }}>
            ⏰ All posts scheduled for <strong>5:30am UK time</strong> — your proven optimal window
          </div>
          <div className="calendar-grid">
            {calendar.map((day, i) => {
              const d = getDay(day.offset);
              const isToday = day.offset === 0;
              return (
                <div key={i} className={`calendar-day ${isToday ? 'highlight' : ''}`}>
                  <div className="day-name">{d.name}{isToday ? ' · Today' : ''}</div>
                  <div className="day-date">{d.date}</div>
                  <div className="content-type-tag">{day.type}</div>
                  <div className="content-idea">{day.idea}</div>
                  <div className="viral-score">
                    <span className="viral-label">Viral:</span>
                    <div className="viral-dots">
                      {[1,2,3,4,5].map(n => <div key={n} className={`viral-dot ${n <= day.viralScore ? 'filled' : ''}`}></div>)}
                    </div>
                  </div>
                  <div className="template-actions" style={{ marginTop: 10 }}>
                    <button
                      className={`btn-copy ${copiedCap === i ? 'copied' : ''}`}
                      onClick={() => copy(day.caption + '\n\n' + day.hashtags, 'cap', i)}
                      style={{ fontSize: 10 }}
                    >
                      {copiedCap === i ? '✓ Copied' : '📋 Caption'}
                    </button>
                    <button
                      className={`btn-copy ${copiedHash === i ? 'copied' : ''}`}
                      onClick={() => copy(day.hashtags, 'hash', i)}
                      style={{ fontSize: 10 }}
                    >
                      {copiedHash === i ? '✓ Copied' : '#️⃣ Tags'}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="card mt-20">
            <div className="card-title">📋 Full Week Content Preview</div>
            {calendar.map((day, i) => {
              const d = getDay(day.offset);
              return (
                <div key={i} style={{ borderBottom: '1px solid var(--border)', padding: '14px 0' }}>
                  <div className="flex items-center justify-between mb-8">
                    <div className="flex items-center gap-12">
                      <span style={{ fontWeight: 700, color: 'var(--gold)', fontSize: 13, minWidth: 80 }}>{d.name}</span>
                      <span className="badge badge-blue">{day.type}</span>
                      <span style={{ fontSize: 13, fontWeight: 500 }}>{day.idea}</span>
                    </div>
                    <div className="flex gap-8">
                      <CopyButton text={day.caption + '\n\n' + day.hashtags} label="Caption" />
                      <CopyButton text={day.hashtags} label="Tags" />
                    </div>
                  </div>
                  <div className="caption-box">{day.caption}</div>
                  <div className="hashtag-cloud">
                    {day.hashtags.split(' ').map((h, j) => <span key={j} className="hashtag-chip">{h}</span>)}
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}

      {activeTab === 'captions' && (
        <>
          <div className="grid-2">
            {captionFormulas.map((f, i) => (
              <div key={i} className="card">
                <div className="flex items-center justify-between mb-12">
                  <div className="card-title" style={{ marginBottom: 0 }}>{f.name}</div>
                  <span className="badge badge-gold">🔥 {f.viralScore}% viral</span>
                </div>

                <div style={{ marginBottom: 12 }}>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 6 }}>Template</div>
                  <div className="email-template" style={{ fontSize: 12 }}>{f.template}</div>
                  <CopyButton text={f.template} label="Copy Template" className="mt-8" />
                </div>

                <div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 6 }}>Example</div>
                  <div className="caption-box">{f.example}</div>
                  <CopyButton text={f.example} label="Copy Example" />
                </div>
              </div>
            ))}
          </div>

          <div className="card mt-20">
            <div className="card-title">🎯 Caption Rules for @thecozyfamily.ai</div>
            <div className="grid-3">
              {[
                { icon: '✅', rule: '3–5 word punchy lines', detail: 'Stops the scroll mid-swipe' },
                { icon: '✅', rule: 'First-person "I" narrative', detail: 'Creates personal emotional pull' },
                { icon: '✅', rule: 'Start with emotion', detail: 'Freeze / I didn\'t / She...' },
                { icon: '✅', rule: 'White space between lines', detail: 'Easier to read fast' },
                { icon: '✅', rule: 'End with soft CTA', detail: 'Save / Share / Does your dog too?' },
                { icon: '❌', rule: 'Never start with "Welcome"', detail: 'Generic openers kill reach' },
              ].map((item, i) => (
                <div key={i} style={{ background: 'var(--bg-card2)', borderRadius: 8, padding: '12px 14px', border: '1px solid var(--border)' }}>
                  <div style={{ fontSize: 16, marginBottom: 6 }}>{item.icon}</div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 3 }}>{item.rule}</div>
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{item.detail}</div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {activeTab === 'hashtags' && (
        <>
          <div className="grid-2">
            {hashtagSets.map((set, i) => (
              <div key={i} className="card">
                <div className="flex items-center justify-between mb-8">
                  <div className="card-title" style={{ marginBottom: 0 }}>{set.name}</div>
                  <CopyButton text={set.tags} label="Copy All" />
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 12 }}>Use: {set.use}</div>
                <div className="hashtag-cloud">
                  {set.tags.split(' ').map((tag, j) => (
                    <span key={j} className="hashtag-chip" onClick={() => { navigator.clipboard.writeText(tag); }}>{tag}</span>
                  ))}
                </div>
              </div>
            ))}
          </div>

          <div className="card mt-20">
            <div className="card-title">📊 Hashtag Strategy Tips</div>
            <div className="grid-3">
              {[
                { icon: '🎯', tip: '20–25 hashtags per post', detail: 'Mix sizes: 3 large + 12 medium + 10 niche' },
                { icon: '📌', tip: 'Always include #CozyfamilyAI', detail: 'Build your own branded hashtag community' },
                { icon: '🔄', tip: 'Rotate sets weekly', detail: 'Avoid hashtag fatigue and shadow bans' },
                { icon: '📈', tip: 'Research trending niche tags', detail: 'Check Reels Tab → Trending this week' },
                { icon: '🚫', tip: 'Avoid banned hashtags', detail: '#familylove #love can suppress reach' },
                { icon: '💬', tip: 'Add hashtags in caption', detail: 'More reach than first comment in 2025' },
              ].map((item, i) => (
                <div key={i} style={{ background: 'var(--bg-card2)', borderRadius: 8, padding: '12px 14px', border: '1px solid var(--border)' }}>
                  <div style={{ fontSize: 16, marginBottom: 6 }}>{item.icon}</div>
                  <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 3 }}>{item.tip}</div>
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{item.detail}</div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
