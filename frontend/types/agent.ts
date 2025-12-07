export interface Agent {
  id: string;
  name: string;
  role: string;
  status: 'working' | 'resting' | 'break';
  cubicleId: number; // Maps to a specific desk position
  sentiment: number; // -1 to 1
  currentAction?: string;
}

export interface MarketSignal {
  timestamp: number;
  data: any;
}

