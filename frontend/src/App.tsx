import { useState, useEffect, useMemo } from 'react'
import './index.css'

interface Set {
  reps: number;
  weight: number;
  unit: 'kg' | 'lbs';
}

interface Exercise {
  name: string;
  sets: Set[];
}

interface WorkoutHistoryItem {
  sk: string;
  name: string;
  exercises: {
    exercise_name: string;
    sets: Set[];
  }[];
}

const COMMON_EXERCISES = [
  "Squats", "Bench Press", "Deadlift", "Overhead Press", "Barbell Row", 
  "Pull Ups", "Dips", "Lunges", "Leg Press", "Lateral Raise", 
  "Bicep Curls", "Tricep Extensions", "Plank", "Leg Curls"
];

const KG_TO_LBS = 2.20462;
const BASE_URL = import.meta.env.VITE_API_URL || '/api';

function App() {
  const [token, setToken] = useState<string | null>(localStorage.getItem('set_token'));
  const [user, setUser] = useState<string | null>(localStorage.getItem('set_user'));
  const [loginUsername, setLoginUsername] = useState('');

  const [view, setView] = useState<'workout' | 'history'>('workout');
  const [workoutName, setWorkoutName] = useState('New Workout');
  const [exercises, setExercises] = useState<Exercise[]>([]);
  const [history, setHistory] = useState<WorkoutHistoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [isAdding, setIsAdding] = useState(false);
  const [newExName, setNewExName] = useState("");
  const [searchIndex, setSearchIndex] = useState(0);
  const [editingWorkoutId, setEditingWorkoutId] = useState<string | null>(null);
  const [editingWorkoutDate, setEditingWorkoutDate] = useState<string | null>(null);

  const filteredExercises = useMemo(() => {
    if (!newExName.trim()) return COMMON_EXERCISES;
    return COMMON_EXERCISES.filter(ex => 
      ex.toLowerCase().includes(newExName.toLowerCase())
    );
  }, [newExName]);

  const fetchHistory = async () => {
    if (!token) return;
    setLoading(true);
    try {
      const response = await fetch(`${BASE_URL}/workouts`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      const data = await response.json();
      setHistory(data.sort((a: WorkoutHistoryItem, b: WorkoutHistoryItem) => 
        new Date(b.sk.split('#')[1]).getTime() - new Date(a.sk.split('#')[1]).getTime()
      ));
    } catch (error) {
      console.error('Error fetching history:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token && view === 'history') {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      void fetchHistory();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, view]);

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    if (loginUsername.trim()) {
      const mockToken = `mock_${loginUsername.trim()}`;
      setToken(mockToken);
      setUser(loginUsername.trim());
      localStorage.setItem('set_token', mockToken);
      localStorage.setItem('set_user', loginUsername.trim());
    }
  };

  const handleLogout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('set_token');
    localStorage.removeItem('set_user');
    setView('workout');
  };

  const deleteWorkout = async (sk: string) => {
    if (!token) return;
    const parts = sk.split('#');
    const date = parts[1];
    const workoutId = parts[2];

    if (!window.confirm('Are you sure you want to delete this workout?')) {
      return;
    }

    try {
      const response = await fetch(`${BASE_URL}/workouts/${workoutId}?date=${encodeURIComponent(date)}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        fetchHistory();
      } else {
        alert('Failed to delete workout.');
      }
    } catch {
      alert('Error connecting to backend.');
    }
  };

  const startEdit = (workout: WorkoutHistoryItem) => {
    const parts = workout.sk.split('#');
    const date = parts[1];
    const workoutId = parts[2];

    setEditingWorkoutId(workoutId);
    setEditingWorkoutDate(date);
    setWorkoutName(workout.name);
    setExercises(workout.exercises.map(ex => ({
      name: ex.exercise_name,
      sets: ex.sets
    })));
    setView('workout');
  };

  const addExercise = (name?: string) => {
    const finalName = name || newExName.trim();
    if (finalName) {
      setExercises([...exercises, { name: finalName, sets: [] }]);
      setNewExName("");
      setSearchIndex(-1);
      setIsAdding(false);
    }
  };

  const removeExercise = (index: number) => {
    const newExercises = [...exercises];
    newExercises.splice(index, 1);
    setExercises(newExercises);
  };

  const addSet = (exerciseIndex: number) => {
    const newExercises = [...exercises];
    const lastSet = newExercises[exerciseIndex].sets.length > 0 
      ? newExercises[exerciseIndex].sets[newExercises[exerciseIndex].sets.length - 1]
      : { reps: 10, weight: 0, unit: 'kg' as const };
    
    newExercises[exerciseIndex].sets.push({ ...lastSet });
    setExercises(newExercises);
  };

  const updateSet = (exerciseIndex: number, setIndex: number, field: keyof Set, value: string | number) => {
    const newExercises = [...exercises];
    const targetSet = newExercises[exerciseIndex].sets[setIndex];
    if (field === 'weight') {
      targetSet.weight = typeof value === 'string' ? parseFloat(value) : value;
    } else if (field === 'reps') {
      targetSet.reps = typeof value === 'string' ? parseInt(value) : value;
    }
    setExercises(newExercises);
  };

  const toggleUnit = (exerciseIndex: number, setIndex: number) => {
    const newExercises = [...exercises];
    const setItem = newExercises[exerciseIndex].sets[setIndex];
    const currentUnit = setItem.unit || 'kg';
    const newUnit = currentUnit === 'kg' ? 'lbs' : 'kg';
    
    let newWeight = setItem.weight;
    if (newWeight > 0) {
      if (newUnit === 'lbs') {
        newWeight = Math.round(newWeight * KG_TO_LBS * 10) / 10;
      } else {
        newWeight = Math.round((newWeight / KG_TO_LBS) * 10) / 10;
      }
    }
    
    setItem.unit = newUnit;
    setItem.weight = newWeight;
    setExercises(newExercises);
  };

  const saveWorkout = async () => {
    if (!token) return;
    interface WorkoutPayload {
      name: string;
      exercises: {
        exercise_name: string;
        sets: Set[];
      }[];
      id?: string;
      date?: string | null;
    }

    const workout: WorkoutPayload = {
      name: workoutName,
      exercises: exercises.map(ex => ({
        exercise_name: ex.name,
        sets: ex.sets
      })),
    };

    if (editingWorkoutId) {
      workout.id = editingWorkoutId;
      workout.date = editingWorkoutDate;
    }
    
    try {
      const url = editingWorkoutId 
        ? `${BASE_URL}/workouts/${editingWorkoutId}?old_date=${encodeURIComponent(editingWorkoutDate!)}`
        : `${BASE_URL}/workouts`;
      
      const response = await fetch(url, {
        method: editingWorkoutId ? 'PUT' : 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(workout),
      });
      
      if (response.ok) {
        alert(editingWorkoutId ? 'Workout updated!' : 'Workout saved!');
        setExercises([]);
        setWorkoutName('New Workout');
        setEditingWorkoutId(null);
        setEditingWorkoutDate(null);
        setView('history');
        fetchHistory();
      } else {
        alert('Failed to save workout.');
      }
    } catch {
      alert('Error connecting to backend.');
    }
  };

  if (!token) {
    return (
      <div className="app-container" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh' }}>
        <div className="card" style={{ width: '100%', maxWidth: '360px' }}>
          <h1 style={{ textAlign: 'center', marginBottom: '2.5rem' }}>set</h1>
          <form onSubmit={handleLogin}>
            <div className="set-input-group" style={{ marginBottom: '1.5rem' }}>
              <label htmlFor="username" className="set-input-label">Username</label>
              <input 
                id="username"
                type="text" 
                value={loginUsername}
                onChange={(e) => setLoginUsername(e.target.value)}
                placeholder="Enter your username"
                required
                autoFocus
              />
            </div>
            <button className="btn" type="submit" style={{ width: '100%', padding: '0.8rem' }}>
              Login
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="app-container">
      <header>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <h1>set</h1>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', borderLeft: '1px solid var(--border-color)', paddingLeft: '1rem' }}>
            {user}
          </span>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button 
            className={`btn ${view === 'workout' ? '' : 'btn-secondary'}`} 
            onClick={() => setView('workout')}
          >
            Log
          </button>
          <button 
            className={`btn ${view === 'history' ? '' : 'btn-secondary'}`} 
            onClick={() => { setView('history'); }}
          >
            History
          </button>
          <button className="btn btn-secondary" onClick={handleLogout} title="Sign Out">
            Logout
          </button>
        </div>
      </header>

      {view === 'workout' ? (
        <div className="card">
          <input 
            style={{ fontSize: '1.2rem', fontWeight: 'bold', marginBottom: '1rem', border: 'none', background: 'transparent', padding: '0', color: 'white' }}
            value={workoutName} 
            onChange={(e) => setWorkoutName(e.target.value)} 
            placeholder="Workout Name"
          />
          
          <div className="workout-grid">
            {exercises.map((ex, exIdx) => (
              <div key={exIdx} className="exercise-row">
                <div className="exercise-header">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span style={{ fontWeight: 600 }}>{ex.name}</span>
                    <button 
                      onClick={() => removeExercise(exIdx)}
                      style={{ background: 'transparent', border: 'none', color: '#ef4444', cursor: 'pointer', fontSize: '0.8rem' }}
                    >
                      ✕
                    </button>
                  </div>
                  <button className="btn btn-secondary" style={{ padding: '0.2rem 0.6rem', fontSize: '0.8rem' }} onClick={() => addSet(exIdx)}>
                    + Set
                  </button>
                </div>
                
                <div className="set-list">
                  {ex.sets.map((set, sIdx) => (
                    <div key={sIdx} className="set-item">
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: '0.8rem', fontWeight: '800', color: 'var(--primary-color)' }}>SET {sIdx + 1}</span>
                      </div>
                      
                      <div className="set-input-row">
                        <div className="set-input-group">
                          <label className="set-input-label">Weight</label>
                          <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                            <input 
                              type="number" 
                              value={set.weight || ''} 
                              placeholder="0"
                              onChange={(e) => updateSet(exIdx, sIdx, 'weight', parseFloat(e.target.value))} 
                              style={{ paddingRight: '2.5rem' }}
                            />
                            <button 
                              className="unit-badge" 
                              onClick={() => toggleUnit(exIdx, sIdx)}
                              style={{ 
                                border: 'none', 
                                cursor: 'pointer', 
                                background: 'var(--primary-color)', 
                                color: 'white',
                                borderRadius: '4px',
                                padding: '2px 6px',
                                textTransform: 'uppercase',
                                pointerEvents: 'auto'
                              }}
                            >
                              {set.unit || 'kg'}
                            </button>
                          </div>
                        </div>
                        
                        <div className="set-input-group">
                          <label className="set-input-label">Reps</label>
                          <input 
                            type="number" 
                            value={set.reps || ''} 
                            placeholder="0"
                            onChange={(e) => updateSet(exIdx, sIdx, 'reps', parseInt(e.target.value))} 
                            style={{ textAlign: 'center' }}
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {!isAdding ? (
            <button className="btn" style={{ width: '100%', marginTop: '1.5rem', background: '#2d2d2d', border: '1px dashed var(--border-color)' }} onClick={() => setIsAdding(true)}>
              + Add Exercise
            </button>
          ) : (
            <div className="card" style={{ marginTop: '1.5rem', border: '1px solid var(--primary-color)' }}>
              <div style={{ position: 'relative' }}>
                <input 
                  autoFocus
                  placeholder="Search exercise..."
                  value={newExName}
                  onChange={(e) => {
                    setNewExName(e.target.value);
                    setSearchIndex(-1);
                  }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      if (filteredExercises.length > 0) {
                        addExercise(filteredExercises[searchIndex]);
                      } else {
                        addExercise();
                      }
                    } else if (e.key === 'ArrowDown') {
                      e.preventDefault();
                      setSearchIndex(prev => Math.min(prev + 1, filteredExercises.length - 1));
                    } else if (e.key === 'ArrowUp') {
                      e.preventDefault();
                      setSearchIndex(prev => Math.max(prev - 1, 0));
                    } else if (e.key === 'Escape') {
                      setIsAdding(false);
                    }
                  }}
                  style={{ marginBottom: '1rem' }}
                />
                {filteredExercises.length > 0 && newExName.trim() !== "" && (
                  <div className="exercise-suggestions">
                    {filteredExercises.map((ex, i) => (
                      <div 
                        key={ex} 
                        className={`suggestion-item ${i === searchIndex ? 'active' : ''}`}
                        onClick={() => addExercise(ex)}
                        onMouseEnter={() => setSearchIndex(i)}
                      >
                        {ex}
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button className="btn" style={{ flex: 1 }} onClick={() => addExercise()}>Add</button>
                <button className="btn btn-secondary" style={{ flex: 1 }} onClick={() => setIsAdding(false)}>Cancel</button>
              </div>
            </div>
          )}
          
          {exercises.length > 0 && (
            <button className="btn" style={{ width: '100%', background: 'var(--success-color)', padding: '1rem', fontSize: '1rem', marginTop: '1.5rem' }} onClick={saveWorkout}>
              {editingWorkoutId ? 'Update Workout' : 'Save Workout'}
            </button>
          )}
        </div>
      ) : (
        <div className="history-list">
          {loading ? (
            <p style={{ textAlign: 'center' }}>Loading history...</p>
          ) : history.length === 0 ? (
            <p style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '2rem' }}>No workouts found.</p>
          ) : (
            history.map((w, idx) => (
              <div key={idx} className="card" style={{ marginBottom: '1rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                  <div style={{ display: 'flex', flexDirection: 'column' }}>
                    <strong style={{ fontSize: '1.1rem' }}>{w.name}</strong>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                      {new Date(w.sk.split('#')[1]).toLocaleDateString()}
                    </span>
                  </div>
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button 
                      onClick={() => startEdit(w)}
                      style={{ background: 'transparent', border: 'none', color: 'var(--primary-color)', cursor: 'pointer', fontSize: '0.9rem', padding: '0.5rem' }}
                      title="Edit workout"
                    >
                      ✎
                    </button>
                    <button 
                      onClick={() => deleteWorkout(w.sk)}
                      style={{ background: 'transparent', border: 'none', color: '#ef4444', cursor: 'pointer', fontSize: '0.9rem', padding: '0.5rem' }}
                      title="Delete workout"
                    >
                      ✕
                    </button>
                  </div>
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                  {w.exercises?.map((ex, eIdx: number) => (
                    <div key={eIdx} style={{ fontSize: '0.8rem', background: '#2d2d2d', padding: '0.2rem 0.5rem', borderRadius: '4px' }}>
                      {ex.exercise_name} ({ex.sets?.length} sets)
                    </div>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}

export default App
