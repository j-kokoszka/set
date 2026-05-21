import { useState, useEffect, useMemo, useRef } from 'react'
import './index.css'
import { parseBackendError } from './utils/error'
import { generateCodeVerifier, generateCodeChallenge, base64UrlDecode } from './utils/auth'
import FeedbackButton from './FeedbackButton'

interface Set {
  reps: number;
  weight: number;
  unit: 'kg' | 'lbs';
  difficulty?: 'easy' | 'moderate' | 'hard' | 'pass';
  completed?: boolean;
}

interface Exercise {
  id?: string;
  name: string;
  sets: Set[];
}

interface StandardExercise {
  id: string;
  name: string;
  primaryMuscles: string[];
  category: string;
}

const MUSCLE_GROUPS: Record<string, string[]> = {
  "Upper Body": ["chest", "shoulders", "biceps", "triceps", "forearms", "lats", "middle back", "traps", "lower back"],
  "Lower Body": ["quadriceps", "hamstrings", "glutes", "calves", "adductors", "abductors"],
  "Other": ["abdominals", "neck", "cardio"]
};

interface WorkoutHistoryItem {
  sk: string;
  name: string;
  exercises: {
    exercise_id?: string;
    exercise_name: string;
    sets: Set[];
  }[];
}

interface RoutineExerciseSet {
  reps?: number;
  weight?: number;
  unit: 'kg' | 'lbs';
}

interface RoutineExercise {
  exercise_id?: string;
  exercise_name: string;
  sets: RoutineExerciseSet[];
}

interface WorkoutRoutine {
  id: string;
  name: string;
  exercises: RoutineExercise[];
}

const KG_TO_LBS = 2.20462;
const BASE_URL = import.meta.env.VITE_API_URL || '/api';
const COGNITO_DOMAIN = import.meta.env.VITE_COGNITO_DOMAIN;
const COGNITO_CLIENT_ID = import.meta.env.VITE_COGNITO_CLIENT_ID;
const APP_URL = window.location.origin;

function App() {
  const [token, setToken] = useState<string | null>(localStorage.getItem('set_token'));
  const [user, setUser] = useState<string | null>(localStorage.getItem('set_user'));
  const [loginUsername, setLoginUsername] = useState('');

  const [view, setView] = useState<'workout' | 'history' | 'routines'>('workout');
  const [workoutName, setWorkoutName] = useState('New Workout');
  const [exercises, setExercises] = useState<Exercise[]>([]);
  const [allExercises, setAllExercises] = useState<StandardExercise[]>([]);
  const [history, setHistory] = useState<WorkoutHistoryItem[]>([]);
  const [routines, setRoutines] = useState<WorkoutRoutine[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingExercises, setLoadingExercises] = useState(false);
  const [isAdding, setIsAdding] = useState(false);
  const [isSelectingRoutine, setIsSelectingRoutine] = useState(false);
  const [newExName, setNewExName] = useState("");
  const [searchIndex, setSearchIndex] = useState(-1);
  const [editingWorkoutId, setEditingWorkoutId] = useState<string | null>(null);
  const [editingWorkoutDate, setEditingWorkoutDate] = useState<string | null>(null);
  const [editingRoutineId, setEditingRoutineId] = useState<string | null>(null);
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  // Navigation state
  const [navPath, setNavPath] = useState<string[]>([]);

  const handleLogout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('set_token');
    localStorage.removeItem('set_refresh_token');
    localStorage.removeItem('set_user');
    setView('workout');
  };

  const refreshPromise = useRef<Promise<string | null> | null>(null);

  const refreshIdToken = async () => {
    if (refreshPromise.current) {
      return refreshPromise.current;
    }

    refreshPromise.current = (async () => {
      const refreshToken = localStorage.getItem('set_refresh_token');
      if (!refreshToken || !COGNITO_DOMAIN || !COGNITO_CLIENT_ID) {
        handleLogout();
        return null;
      }

      try {
        const response = await fetch(`https://${COGNITO_DOMAIN}/oauth2/token`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: new URLSearchParams({
            grant_type: 'refresh_token',
            client_id: COGNITO_CLIENT_ID,
            refresh_token: refreshToken
          })
        });

        if (response.ok) {
          const data = await response.json();
          const newIdToken = data.id_token;
          const newRefreshToken = data.refresh_token;
          if (newIdToken) {
            setToken(newIdToken);
            localStorage.setItem('set_token', newIdToken);
            if (newRefreshToken) {
              localStorage.setItem('set_refresh_token', newRefreshToken);
            }
            return newIdToken;
          }
        } else {
          handleLogout();
        }
      } catch (e) {
        console.error('Failed to refresh token', e);
      } finally {
        refreshPromise.current = null;
      }
      return null;
    })();

    return refreshPromise.current;
  };

  const getValidToken = async () => {
    if (!token) return null;
    if (token.startsWith('mock_')) return token;

    const parts = token.split('.');
    if (parts.length !== 3) {
      handleLogout();
      return null;
    }

    const payload = base64UrlDecode(parts[1]);
    if (!payload || typeof payload.exp !== 'number') {
      handleLogout();
      return null;
    }

    const currentTime = Math.floor(Date.now() / 1000);
    // Refresh if expiring in less than 5 minutes
    if (payload.exp - currentTime < 300) {
      const newToken = await refreshIdToken();
      return newToken;
    }
    return token;
  };

  const fetchExercises = async () => {
    setLoadingExercises(true);
    try {
      const response = await fetch(`${BASE_URL}/exercises`);
      if (!response.ok) throw new Error('Failed to fetch exercises');
      const data = await response.json();
      setAllExercises(data);
    } catch (error) {
      console.error('Error fetching exercises:', error);
      alert('Could not load exercise database. Some features may be limited.');
    } finally {
      setLoadingExercises(false);
    }
  };

  const filteredExercises = useMemo(() => {
    if (!newExName.trim()) return allExercises.slice(0, 15); // Show first 15 as default suggestions
    return allExercises.filter(ex => 
      ex.name.toLowerCase().includes(newExName.toLowerCase())
    ).slice(0, 10); // Limit search results to top 10 for performance
  }, [newExName, allExercises]);

  const navExercises = useMemo(() => {
    if (navPath.length !== 2) return [];
    const targetMuscle = navPath[1].toLowerCase().trim();
    return allExercises.filter(ex => 
      ex.primaryMuscles?.some(m => m.toLowerCase().trim() === targetMuscle)
    );
  }, [navPath, allExercises]);

  const fetchHistory = async () => {
    const validToken = await getValidToken();
    if (!validToken) return;
    setLoading(true);
    try {
      const response = await fetch(`${BASE_URL}/workouts`, {
        headers: {
          'Authorization': `Bearer ${validToken}`
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

  const fetchRoutines = async () => {
    const validToken = await getValidToken();
    if (!validToken) return;
    setLoading(true);
    try {
      const response = await fetch(`${BASE_URL}/routines`, {
        headers: {
          'Authorization': `Bearer ${validToken}`
        }
      });
      if (response.ok) {
        const data = await response.json();
        setRoutines(data);
      } else {
        console.error('Failed to fetch routines');
      }
    } catch (e) {
      console.error('Error fetching routines:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const handleAuth = async () => {
      // 1. Check for 'code' in URL query (returning from Cognito with Auth Code Flow)
      const params = new URLSearchParams(window.location.search);
      const code = params.get('code');
      
      if (code) {
        const codeVerifier = sessionStorage.getItem('code_verifier');
        if (codeVerifier) {
          try {
            const response = await fetch(`https://${COGNITO_DOMAIN}/oauth2/token`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
              body: new URLSearchParams({
                grant_type: 'authorization_code',
                client_id: COGNITO_CLIENT_ID!,
                code: code,
                redirect_uri: APP_URL,
                code_verifier: codeVerifier
              })
            });

            if (response.ok) {
              const data = await response.json();
              const idToken = data.id_token;
              const refreshToken = data.refresh_token;
              
              if (idToken) {
                setToken(idToken);
                localStorage.setItem('set_token', idToken);
                if (refreshToken) {
                  localStorage.setItem('set_refresh_token', refreshToken);
                }
                
                const payload = base64UrlDecode(idToken.split('.')[1]);
                const username = payload?.email || payload?.['cognito:username'] || payload?.sub || 'Authenticated User';
                setUser(username);
                localStorage.setItem('set_user', username);
              }
            }
          } catch (e) {
            console.error('Token exchange failed', e);
          } finally {
            sessionStorage.removeItem('code_verifier');
            window.history.replaceState(null, '', window.location.pathname);
          }
        }
      }

      // 2. Legacy/Fallback: Implicit Flow check (checking for tokens in the hash)
      const hash = window.location.hash;
      if (hash) {
        const hashParams = new URLSearchParams(hash.substring(1));
        const idToken = hashParams.get('id_token') || hashParams.get('access_token');

        if (idToken) {
          setToken(idToken);
          localStorage.setItem('set_token', idToken);
          
          const payload = base64UrlDecode(idToken.split('.')[1]);
          const username = payload?.email || payload?.['cognito:username'] || payload?.sub || 'Authenticated User';
          setUser(username);
          localStorage.setItem('set_user', username);

          window.history.replaceState(null, '', window.location.pathname);
        }
      }
    };

    void handleAuth();
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void fetchExercises();
  }, []);

  useEffect(() => {
    if (token) {
      if (view === 'history') {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        void fetchHistory();
      } else if (view === 'routines') {
        void fetchRoutines();
      }
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

  const handleGoogleLogin = async () => {
    if (!COGNITO_DOMAIN || !COGNITO_CLIENT_ID) {
      alert('Google SSO is not configured for this environment.');
      return;
    }

    // Secure Authorization Code Flow with PKCE
    const codeVerifier = generateCodeVerifier();
    sessionStorage.setItem('code_verifier', codeVerifier);
    const codeChallenge = await generateCodeChallenge(codeVerifier);

    const loginUrl = `https://${COGNITO_DOMAIN}/oauth2/authorize?` + new URLSearchParams({
      client_id: COGNITO_CLIENT_ID,
      response_type: 'code',
      scope: 'email openid profile',
      redirect_uri: APP_URL,
      code_challenge_method: 'S256',
      code_challenge: codeChallenge,
      identity_provider: 'Google' // Direct to Google login
    }).toString();

    window.location.href = loginUrl;
  };

  const deleteRoutine = async (id: string) => {
    const validToken = await getValidToken();
    if (!validToken) return;
    if (!window.confirm('Are you sure you want to delete this routine?')) return;

    try {
      const response = await fetch(`${BASE_URL}/routines/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${validToken}` }
      });
      if (response.ok) fetchRoutines();
    } catch (e) {
      console.error('Error deleting routine:', e);
      alert('Error deleting routine');
    }
  };

  const startFromRoutine = (routine: WorkoutRoutine) => {
    setWorkoutName(routine.name);
    setExercises(routine.exercises.map(ex => ({
      id: ex.exercise_id,
      name: ex.exercise_name,
      sets: ex.sets.map(s => ({
        reps: s.reps || 10,
        weight: s.weight || 0,
        unit: s.unit
      }))
    })));
    setIsSelectingRoutine(false);
  };

  const deleteWorkout = async (sk: string) => {
    const validToken = await getValidToken();
    if (!validToken) return;
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
          'Authorization': `Bearer ${validToken}`
        }
      });

      if (response.ok) {
        fetchHistory();
      } else {
        const errorMessage = await parseBackendError(response, 'Failed to delete workout');
        alert(errorMessage);
      }
    } catch (error) {
      alert(`Error connecting to backend: ${error instanceof Error ? error.message : 'Unknown error'}`);
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
      id: ex.exercise_id,
      name: ex.exercise_name,
      sets: ex.sets
    })));
    setView('workout');
  };

  const startRoutineEdit = (routine: WorkoutRoutine) => {
    setEditingRoutineId(routine.id);
    setWorkoutName(routine.name);
    setExercises(routine.exercises.map(ex => ({
      id: ex.exercise_id,
      name: ex.exercise_name,
      sets: ex.sets.map(s => ({
        reps: s.reps || 10,
        weight: s.weight || 0,
        unit: s.unit
      }))
    })));
    setView('workout');
  };

  const clearWorkout = () => {
    if (exercises.length === 0) return;
    if (window.confirm('Are you sure you want to clear all exercises from the current log?')) {
      setExercises([]);
      setWorkoutName('New Workout');
      setEditingWorkoutId(null);
      setEditingWorkoutDate(null);
      setEditingRoutineId(null);
    }
  };

  const addExercise = (nameOrEx?: string | StandardExercise) => {
    let name: string;
    let id: string | undefined;

    if (typeof nameOrEx === 'object' && nameOrEx !== null) {
      name = nameOrEx.name;
      id = nameOrEx.id;
    } else if (typeof nameOrEx === 'string') {
      name = nameOrEx;
      id = undefined;
    } else {
      name = newExName.trim();
      id = undefined;
    }

    if (name) {
      setExercises([...exercises, { id, name, sets: [] }]);
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
    setExercises(prev => prev.map((ex, exIdx) => {
      if (exIdx !== exerciseIndex) return ex;
      const lastSet = ex.sets.length > 0 
        ? ex.sets[ex.sets.length - 1]
        : { reps: 10, weight: 0, unit: 'kg' as const };
      return {
        ...ex,
        sets: [...ex.sets, { ...lastSet, completed: false, difficulty: undefined }]
      };
    }));
  };

  const removeSet = (exerciseIndex: number, setIndex: number) => {
    setExercises(prev => prev.map((ex, exIdx) => {
      if (exIdx !== exerciseIndex) return ex;
      return {
        ...ex,
        sets: ex.sets.filter((_, sIdx) => sIdx !== setIndex)
      };
    }));
  };

  const updateSet = <K extends keyof Set>(exerciseIndex: number, setIndex: number, field: K, value: Set[K]) => {
    setExercises(prev => prev.map((ex, exIdx) => {
      if (exIdx !== exerciseIndex) return ex;
      return {
        ...ex,
        sets: ex.sets.map((s, sIdx) => {
          if (sIdx !== setIndex) return s;
          const updatedSet = { ...s, [field]: value };
          if (field === 'weight') {
            updatedSet.weight = typeof value === 'string' ? parseFloat(value) : value as number;
          } else if (field === 'reps') {
            updatedSet.reps = typeof value === 'string' ? parseInt(value) : value as number;
          } else if (field === 'difficulty') {
            updatedSet.difficulty = value as Set['difficulty'];
            updatedSet.completed = true;
          } else if (field === 'completed') {
            updatedSet.completed = value as boolean;
          }
          return updatedSet;
        })
      };
    }));
  };


  const toggleUnit = (exerciseIndex: number, setIndex: number) => {
    setExercises(prev => prev.map((ex, exIdx) => {
      if (exIdx !== exerciseIndex) return ex;
      return {
        ...ex,
        sets: ex.sets.map((s, sIdx) => {
          if (sIdx !== setIndex) return s;
          const currentUnit = s.unit || 'kg';
          const newUnit = currentUnit === 'kg' ? 'lbs' : 'kg';
          let newWeight = s.weight;
          if (newWeight > 0) {
            if (newUnit === 'lbs') {
              newWeight = Math.round(newWeight * KG_TO_LBS * 10) / 10;
            } else {
              newWeight = Math.round((newWeight / KG_TO_LBS) * 10) / 10;
            }
          }
          return { ...s, unit: newUnit, weight: newWeight };
        })
      };
    }));
  };

  const saveWorkout = async () => {
    const validToken = await getValidToken();
    if (!validToken) return;
    interface WorkoutPayload {
      name: string;
      exercises: {
        exercise_id?: string;
        exercise_name: string;
        sets: Set[];
      }[];
      id?: string;
      date?: string | null;
    }

    const workout: WorkoutPayload = {
      name: workoutName,
      exercises: exercises.map(ex => ({
        exercise_id: ex.id,
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
          'Authorization': `Bearer ${validToken}`
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
        const errorMessage = await parseBackendError(response, 'Failed to save workout');
        alert(errorMessage);
      }
    } catch (e) {
      console.error('Error saving workout:', e);
      alert(`Error connecting to backend: ${e instanceof Error ? e.message : 'Unknown error'}`);
    }
  };

  const saveRoutine = async () => {
    const validToken = await getValidToken();
    if (!validToken) return;
    const routine: Partial<WorkoutRoutine> = {
      name: workoutName,
      exercises: exercises.map(ex => ({
        exercise_id: ex.id,
        exercise_name: ex.name,
        sets: ex.sets.map(s => ({
          reps: s.reps,
          weight: s.weight,
          unit: s.unit
        }))
      }))
    };

    if (editingRoutineId) routine.id = editingRoutineId;

    try {
      const response = await fetch(`${BASE_URL}/routines${editingRoutineId ? `/${editingRoutineId}` : ''}`, {
        method: editingRoutineId ? 'PUT' : 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${validToken}`
        },
        body: JSON.stringify(routine)
      });
      if (response.ok) {
        alert(editingRoutineId ? 'Routine updated!' : 'Routine saved!');
        setEditingRoutineId(null);
        setWorkoutName('New Workout');
        setExercises([]);
        setView('routines');
        fetchRoutines();
      } else {
        const errorMessage = await parseBackendError(response, 'Failed to save routine');
        alert(errorMessage);
      }
    } catch (e) {
      console.error('Error saving routine:', e);
      alert('Error saving routine');
    }
  };

  if (!token) {
    return (
      <div className="login-container">
        <div className="card login-card">
          <h1 className="login-title">set</h1>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <button 
              className="btn" 
              onClick={handleGoogleLogin}
              style={{ 
                background: 'white', 
                color: '#3c4043', 
                border: '1px solid #dadce0',
              }}
            >
              <img src="https://www.gstatic.com/images/branding/product/1x/gsa_512dp.png" alt="Google" style={{ width: '20px', height: '20px' }} />
              Sign in with Google
            </button>

            {(import.meta.env.DEV || import.meta.env.VITE_ENABLE_MOCK_LOGIN === 'true') && (
              <>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', margin: '0.5rem 0' }}>
                  <div style={{ flex: 1, height: '1px', background: 'var(--border-color)' }}></div>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>or mock login</span>
                  <div style={{ flex: 1, height: '1px', background: 'var(--border-color)' }}></div>
                </div>

                <form onSubmit={handleLogin}>
                  <div className="set-input-group mb-1">
                    <label htmlFor="username" className="set-input-label">Username</label>
                    <input 
                      id="username"
                      type="text" 
                      value={loginUsername}
                      onChange={(e) => setLoginUsername(e.target.value)}
                      placeholder="Enter your username"
                      required
                    />
                  </div>
                  <button className="btn btn-secondary" type="submit">
                    Mock Login
                  </button>
                </form>
              </>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="app-container">
      <header>
        <div className="header-brand">
          <h1>set</h1>
          <span className="user-tag">{user}</span>
        </div>

        <button className="hamburger" onClick={() => setIsMenuOpen(!isMenuOpen)} aria-label="Toggle menu">
          {isMenuOpen ? '✕' : '☰'}
        </button>

        <div className={`nav-menu ${isMenuOpen ? 'open' : ''}`}>
          <button 
            className={`btn btn-small ${view === 'workout' ? '' : 'btn-secondary'}`} 
            onClick={() => { setView('workout'); setIsMenuOpen(false); }}
          >
            Log
          </button>
          <button 
            className={`btn btn-small ${view === 'history' ? '' : 'btn-secondary'}`} 
            onClick={() => { setView('history'); setIsMenuOpen(false); }}
          >
            History
          </button>
          <button 
            className={`btn btn-small ${view === 'routines' ? '' : 'btn-secondary'}`} 
            onClick={() => { setView('routines'); setIsMenuOpen(false); }}
          >
            Routines
          </button>
          <button 
            className="btn btn-secondary btn-small" 
            onClick={() => { handleLogout(); setIsMenuOpen(false); }} 
            title="Sign Out"
          >
            Logout
          </button>
        </div>
      </header>

      {view === 'workout' ? (
        <div className="card">
          <div className="workout-header">
            <input 
              className="workout-name-input"
              value={workoutName} 
              onChange={(e) => setWorkoutName(e.target.value)} 
              placeholder="Workout Name"
            />
            {!editingWorkoutId && !editingRoutineId && (
              <button 
                className="btn btn-secondary btn-small" 
                style={{ width: 'auto' }}
                onClick={() => setIsSelectingRoutine(true)}
              >
                Start from Routine
              </button>
            )}
          </div>

          {isSelectingRoutine && (
            <div className="modal-overlay" onClick={() => setIsSelectingRoutine(false)}>
              <div className="modal-content" onClick={e => e.stopPropagation()}>
                <h3 className="modal-title">Select a Routine</h3>
                {routines.length === 0 ? (
                  <p style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '1rem' }}>No routines found. Create one in the Routines tab!</p>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginBottom: '1.5rem' }}>
                    {routines.map(p => (
                      <button key={p.id} className="btn btn-secondary" style={{ textAlign: 'left', justifyContent: 'flex-start' }} onClick={() => startFromRoutine(p)}>
                        {p.name}
                      </button>
                    ))}
                  </div>
                )}
                <div className="modal-actions">
                  <button className="btn btn-secondary" onClick={() => setIsSelectingRoutine(false)}>Cancel</button>
                </div>
              </div>
            </div>
          )}
          
          <div className="workout-grid">
            {exercises.map((ex, exIdx) => (
              <div key={exIdx} className="exercise-row">
                <div className="exercise-header">
                  <div className="exercise-title">
                    <span>{ex.name}</span>
                    <button 
                      className="btn-danger"
                      onClick={() => removeExercise(exIdx)}
                      title="Remove exercise"
                    >
                      ✕
                    </button>
                  </div>
                  <button className="btn btn-secondary btn-small" onClick={() => addSet(exIdx)}>
                    + Set
                  </button>
                </div>
                
                <div className="set-list">
                  {ex.sets.map((set, sIdx) => (
                    <div key={sIdx} className={`set-item ${set.completed ? 'completed' : ''}`}>
                      <div className="set-header">
                        <div className="flex-center">
                          <span className="set-label">SET {sIdx + 1}</span>
                          {set.completed && <span style={{ color: 'var(--success-color)', fontSize: '0.9rem' }}>✓</span>}
                        </div>
                        <div className="flex-center">
                          <button 
                            className="btn-secondary btn-small"
                            onClick={() => updateSet(exIdx, sIdx, 'completed', !set.completed)}
                            style={{ fontSize: '0.65rem', padding: '0.2rem 0.5rem' }}
                          >
                            {set.completed ? 'Undo' : 'Done'}
                          </button>
                          <button 
                            className="btn-danger"
                            onClick={() => removeSet(exIdx, sIdx)}
                            style={{ padding: '2px 4px', fontSize: '0.7rem' }}
                            title="Remove set"
                          >
                            ✕
                          </button>
                        </div>
                      </div>
                      
                      <div className="set-input-row">
                        <div className="set-input-group">
                          <label className="set-input-label">Weight</label>
                          <div className="input-with-badge">
                            <input 
                              type="number" 
                              value={set.weight || ''} 
                              placeholder="0"
                              onChange={(e) => updateSet(exIdx, sIdx, 'weight', parseFloat(e.target.value))} 
                              style={{ paddingRight: '2.8rem' }}
                            />
                            <button 
                              className="unit-badge" 
                              onClick={() => toggleUnit(exIdx, sIdx)}
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
                          />
                        </div>
                      </div>

                      <div className="difficulty-row">
                        {([
                          { id: 'pass', icon: '⚪' },
                          { id: 'easy', icon: '🟢' },
                          { id: 'moderate', icon: '🟡' },
                          { id: 'hard', icon: '🔴' }
                        ] as const).map(diff => (
                          <button
                            key={diff.id}
                            className={`difficulty-btn ${set.difficulty === diff.id ? 'active' : ''}`}
                            data-diff={diff.id}
                            onClick={() => updateSet(exIdx, sIdx, 'difficulty', diff.id)}
                          >
                            <span className="difficulty-icon">{diff.icon}</span>
                            <span>{diff.id}</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {!isAdding ? (
            <button 
              className="btn btn-secondary" 
              style={{ border: '1px dashed var(--border-color)', marginTop: '1.5rem', background: 'transparent' }} 
              onClick={() => setIsAdding(true)}
            >
              + Add Exercise
            </button>
          ) : (
            <div className="card" style={{ marginTop: '1.5rem', border: '1px solid var(--primary-color)', padding: '1.25rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
                <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                  <button 
                    className="btn btn-secondary btn-small" 
                    onClick={() => {
                      if (navPath.length > 0) {
                        setNavPath(navPath.slice(0, -1));
                      } else {
                        setIsAdding(false);
                      }
                    }}
                  >
                    {navPath.length > 0 ? '← Back' : 'Cancel'}
                  </button>
                  <span style={{ fontSize: '1rem', fontWeight: '700' }}>
                    {navPath.length === 0 ? 'Select Category' : navPath.join(' / ')}
                  </span>
                </div>
              </div>


              {loadingExercises ? (
                <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                  Loading exercise database...
                </div>
              ) : (
                <>
                  {newExName.trim() !== "" && (
                    <div style={{ marginBottom: '1rem' }}>
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
                            if (searchIndex >= 0 && searchIndex < filteredExercises.length) {
                              addExercise(filteredExercises[searchIndex]);
                            } else if (newExName.trim()) {
                              addExercise();
                            }
                          } else if (e.key === 'ArrowDown') {
                            e.preventDefault();
                            setSearchIndex(prev => Math.min(prev + 1, filteredExercises.length - 1));
                          } else if (e.key === 'ArrowUp') {
                            e.preventDefault();
                            setSearchIndex(prev => Math.max(prev - 1, -1));
                          } else if (e.key === 'Escape') {
                            setIsAdding(false);
                          }
                        }}
                      />
                      <div className="exercise-suggestions" style={{ position: 'static', marginTop: '0.5rem' }}>
                        {filteredExercises.length > 0 ? filteredExercises.map((ex, i) => (
                          <div 
                            key={ex.id} 
                            className={`suggestion-item ${i === searchIndex ? 'active' : ''}`}
                            onClick={() => addExercise(ex)}
                            onMouseEnter={() => setSearchIndex(i)}
                          >
                            <div style={{ display: 'flex', flexDirection: 'column' }}>
                              <span style={{ fontWeight: '600' }}>{ex.name}</span>
                              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{ex.primaryMuscles?.join(', ')}</span>
                            </div>
                          </div>
                        )) : (
                          <div className="suggestion-item" onClick={() => addExercise()}>
                            Add custom: "{newExName}"
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {newExName.trim() === "" && (
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', maxHeight: '350px', overflowY: 'auto', padding: '0.25rem' }}>
                      {navPath.length === 0 && (
                        <div style={{ gridColumn: 'span 2', marginBottom: '1rem' }}>
                          <input 
                            autoFocus
                            placeholder="Search exercise..."
                            value={newExName}
                            onChange={(e) => {
                              setNewExName(e.target.value);
                              setSearchIndex(-1);
                            }}
                          />
                        </div>
                      )}

                      {navPath.length === 0 && Object.keys(MUSCLE_GROUPS).map(group => (
                        <button key={group} className="btn btn-secondary" onClick={() => setNavPath([group])}>
                          {group}
                        </button>
                      ))}
                      
                      {navPath.length === 1 && MUSCLE_GROUPS[navPath[0]].map(muscle => (
                        <button key={muscle} className="btn btn-secondary" onClick={() => setNavPath([...navPath, muscle])} style={{ textTransform: 'capitalize' }}>
                          {muscle}
                        </button>
                      ))}

                      {navPath.length === 2 && (
                        navExercises.length === 0 ? (
                          <div style={{ gridColumn: 'span 2', textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                            No exercises found for this muscle group.
                          </div>
                        ) : (
                          navExercises.map(ex => (
                            <button key={ex.id} className="btn btn-secondary" onClick={() => { addExercise(ex); setNavPath([]); }} style={{ fontSize: '0.85rem', textAlign: 'left', height: 'auto', padding: '0.75rem', justifyContent: 'flex-start' }}>
                              {ex.name}
                            </button>
                          ))
                        )
                      )}
                    </div>
                  )}
                </>
              )}
            </div>
          )}
          
          <div style={{ display: 'flex', gap: '1rem', marginTop: '2rem' }}>
            {exercises.length > 0 && (
              <>
                <button 
                  className="btn" 
                  style={{ flex: 2, background: 'var(--success-color)' }} 
                  onClick={saveWorkout}
                >
                  {editingWorkoutId ? 'Update Workout' : 'Save Workout'}
                </button>
                <button 
                  className="btn btn-secondary" 
                  style={{ flex: 1, color: 'var(--danger-color)', borderColor: 'var(--danger-color)' }} 
                  onClick={clearWorkout}
                >
                  Clear
                </button>
              </>
            )}
            {exercises.length > 0 && !editingWorkoutId && (
              <button 
                className="btn btn-secondary" 
                style={{ flex: 1 }} 
                onClick={saveRoutine}
              >
                {editingRoutineId ? 'Update Routine' : 'Save as Routine'}
              </button>
            )}
          </div>
        </div>
      ) : view === 'history' ? (
        <div className="history-list">
          {loading ? (
            <p style={{ textAlign: 'center', padding: '2rem' }}>Loading history...</p>
          ) : history.length === 0 ? (
            <p style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '4rem' }}>No workouts found.</p>
          ) : (
            history.map((w, idx) => (
              <div key={idx} className="card history-item">
                <div className="item-header">
                  <div className="item-title">
                    <span className="item-name">{w.name}</span>
                    <span className="item-meta">
                      {new Date(w.sk.split('#')[1]).toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
                    </span>
                  </div>
                  <div style={{ display: 'flex', gap: '0.25rem' }}>
                    <button 
                      className="btn-secondary btn-small"
                      onClick={() => startEdit(w)}
                      title="Edit workout"
                    >
                      ✎
                    </button>
                    <button 
                      className="btn-danger btn-small"
                      onClick={() => deleteWorkout(w.sk)}
                      title="Delete workout"
                    >
                      ✕
                    </button>
                  </div>
                </div>
                <div className="tag-list">
                  {w.exercises?.map((ex, eIdx: number) => (
                    <span key={eIdx} className="tag">
                      {ex.exercise_name} ({ex.sets?.length})
                    </span>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      ) : (
        <div className="routines-list">
          {loading ? (
            <p style={{ textAlign: 'center', padding: '2rem' }}>Loading routines...</p>
          ) : routines.length === 0 ? (
            <div className="card" style={{ textAlign: 'center', padding: '4rem' }}>
              <p style={{ color: 'var(--text-muted)', marginBottom: '1.5rem' }}>No routines found. Templates help you start workouts faster!</p>
              <button className="btn" style={{ width: 'auto' }} onClick={() => { setView('workout'); setWorkoutName('New Routine'); setExercises([]); setEditingWorkoutId(null); setEditingWorkoutDate(null); setEditingRoutineId(null); }}>
                Create My First Routine
              </button>
            </div>
          ) : (
            <>
              <button 
                className="btn btn-secondary" 
                style={{ marginBottom: '1.5rem', border: '1px dashed var(--border-color)', background: 'transparent' }}
                onClick={() => { setView('workout'); setWorkoutName('New Routine'); setExercises([]); setEditingWorkoutId(null); setEditingWorkoutDate(null); setEditingRoutineId(null); }}
              >
                + Create New Routine
              </button>
              {routines.map((p) => (
              <div key={p.id} className="card routine-item">
                <div className="item-header">
                  <div className="item-title">
                    <span className="item-name">{p.name}</span>
                    <span className="item-meta">{p.exercises.length} exercises</span>
                  </div>
                  <div style={{ display: 'flex', gap: '0.25rem' }}>
                    <button 
                      className="btn btn-small" 
                      onClick={() => startFromRoutine(p)}
                    >
                      Use
                    </button>
                    <button 
                      className="btn-secondary btn-small"
                      onClick={() => startRoutineEdit(p)}
                      title="Edit routine"
                    >
                      ✎
                    </button>
                    <button 
                      className="btn-danger btn-small"
                      onClick={() => deleteRoutine(p.id)}
                      title="Delete routine"
                    >
                      ✕
                    </button>
                  </div>
                </div>
                <div className="tag-list">
                  {p.exercises.map((ex, eIdx) => (
                    <span key={eIdx} className="tag">
                      {ex.exercise_name}
                    </span>
                  ))}
                </div>
              </div>
            ))}
            </>
          )}
        </div>
      )}
      <FeedbackButton getValidToken={getValidToken} />
    </div>
  )
}

export default App
