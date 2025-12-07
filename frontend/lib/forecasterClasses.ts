export const FORECASTER_CLASSES = {
  conservative: {
    name: "Conservative Analyst",
    description: "Risk-averse forecaster that focuses on downside scenarios and base rates. Tends to be skeptical of extreme predictions and anchors toward 50%.",
    traits: [
      "Anchors toward historical base rates",
      "Focuses on downside risks",
      "Skeptical of extreme predictions",
      "Slow to move from baseline"
    ]
  },
  momentum: {
    name: "Momentum Trader",
    description: "Follows market trends and recent price action. Believes the market knows something and moves with recent trade direction.",
    traits: [
      "Follows recent price trends",
      "May chase momentum",
      "Responsive to market signals",
      "Gives weight to recent trades"
    ]
  },
  historical: {
    name: "Historical Analyst",
    description: "Relies heavily on base rates and historical precedent. Looks for analogous past events and is skeptical of 'this time is different' arguments.",
    traits: [
      "Strong focus on base rates",
      "Looks for historical analogies",
      "Skeptical of novel arguments",
      "Anchors to historical frequencies"
    ]
  },
  balanced: {
    name: "Balanced Forecaster",
    description: "Weighs multiple perspectives equally. Tries to identify and correct for biases, may be slow to react to new information.",
    traits: [
      "Considers multiple viewpoints",
      "Attempts to correct biases",
      "Balanced weighting of factors",
      "Methodical approach"
    ]
  },
  realtime: {
    name: "Realtime Reactor",
    description: "Highly responsive to new information. Quick to update predictions based on latest data, but may overreact to noise.",
    traits: [
      "Fast to update predictions",
      "Heavily weights recent info",
      "May overreact to noise",
      "Sensitive to market changes"
    ]
  }
} as const

export type ForecasterClass = keyof typeof FORECASTER_CLASSES
