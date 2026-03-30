def get_justice_loader_html() -> str:
    """
    Returns an HTML/CSS string rendering Lady Justice with scales tipping side to side.
    Embed with st.markdown(get_justice_loader_html(), unsafe_allow_html=True)
    """
    return """
<style>
.justice-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 2rem;
    font-family: serif;
}
.justice-label {
    margin-top: 1rem;
    font-size: 0.9rem;
    color: #888;
    letter-spacing: 0.15em;
    text-transform: uppercase;
}
.scales-svg {
    width: 120px;
    height: 120px;
}
/* The beam rocks on a pivot */
@keyframes rock {
    0%   { transform: rotate(-18deg); }
    50%  { transform: rotate(18deg); }
    100% { transform: rotate(-18deg); }
}
/* Left pan drops then rises */
@keyframes pan-left {
    0%   { transform: translateY(0px); }
    50%  { transform: translateY(12px); }
    100% { transform: translateY(0px); }
}
/* Right pan rises then drops */
@keyframes pan-right {
    0%   { transform: translateY(0px); }
    50%  { transform: translateY(-12px); }
    100% { transform: translateY(0px); }
}
.beam {
    transform-origin: 60px 38px;
    animation: rock 1.6s ease-in-out infinite;
}
.pan-left-group {
    animation: pan-left 1.6s ease-in-out infinite;
}
.pan-right-group {
    animation: pan-right 1.6s ease-in-out infinite;
}
</style>
<div class="justice-container">
  <svg class="scales-svg" viewBox="0 0 120 130" fill="none" xmlns="http://www.w3.org/2000/svg">
    <!-- Pillar -->
    <rect x="57" y="36" width="6" height="80" fill="#b0a080" rx="2"/>
    <!-- Base -->
    <rect x="30" y="114" width="60" height="8" fill="#b0a080" rx="3"/>
    <!-- Top ornament -->
    <circle cx="60" cy="32" r="5" fill="#c8a850"/>
    <!-- Beam (rocks) -->
    <g class="beam">
      <line x1="12" y1="38" x2="108" y2="38" stroke="#c8a850" stroke-width="3" stroke-linecap="round"/>
      <!-- Left chain -->
      <line x1="20" y1="38" x2="20" y2="62" stroke="#c8a850" stroke-width="1.5" stroke-dasharray="3 2"/>
      <!-- Right chain -->
      <line x1="100" y1="38" x2="100" y2="62" stroke="#c8a850" stroke-width="1.5" stroke-dasharray="3 2"/>
      <!-- Left pan (animates independently) -->
      <g class="pan-left-group">
        <ellipse cx="20" cy="66" rx="16" ry="5" fill="#c8a850" opacity="0.85"/>
      </g>
      <!-- Right pan (animates independently) -->
      <g class="pan-right-group">
        <ellipse cx="100" cy="66" rx="16" ry="5" fill="#c8a850" opacity="0.85"/>
      </g>
    </g>
  </svg>
  <div class="justice-label">Analysing&hellip;</div>
</div>
"""
