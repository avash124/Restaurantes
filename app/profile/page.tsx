"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

type Profile = {
  fullName: string;
  sexGender: string;
  location: string;
  conditions: string[];
  allergies: string[];
  profileComplete: true;   
};

const HEALTH_CONDITIONS = [
  { id: "diabetes",        label: "Diabetes" },
  { id: "celiac",          label: "Celiac disease" },
  { id: "highCholesterol", label: "High cholesterol" },
  { id: "pregnancy",       label: "Pregnancy" },
];

const ALLERGY_OPTIONS = [
  { id: "nut",      label: "Nuts" },
  { id: "shellfish", label: "Shellfish" },
  { id: "soy",      label: "Soy" },
  { id: "dairy",    label: "Milk or dairy" },
];

function toggle(arr: string[], value: string): string[] {
  return arr.includes(value) ? arr.filter((v) => v !== value) : [...arr, value];
}

export default function ProfileSetup() {
  const router = useRouter();

  const [fullName,       setFullName]       = useState("");
  const [sexGender,      setSexGender]      = useState("");
  const [location,       setLocation]       = useState("");
  const [conditions,     setConditions]     = useState<string[]>([]);
  const [noneCondition,  setNoneCondition]  = useState(false);
  const [allergies,      setAllergies]      = useState<string[]>([]);
  const [noneAllergy,    setNoneAllergy]    = useState(false);
  const [submitted,      setSubmitted]      = useState<Profile | null>(null);
  const [error,          setError]          = useState("");

  const toggleCondition = (label: string) => {
    setNoneCondition(false);
    setConditions(toggle(conditions, label));
  };

  const selectNoneCondition = () => {
    setNoneCondition(true);
    setConditions([]);
  };

  const toggleAllergy = (label: string) => {
    setNoneAllergy(false);
    setAllergies(toggle(allergies, label));
  };

  const selectNoneAllergy = () => {
    setNoneAllergy(true);
    setAllergies([]);
  };

  const conditionSelected = noneCondition || conditions.length > 0;
  const allergySelected   = noneAllergy   || allergies.length > 0;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!conditionSelected) {
      setError("Please select at least one health condition (or None) to continue.");
      return;
    }
    if (!allergySelected) {
      setError("Please select at least one allergy (or None) to continue.");
      return;
    }
    setError("");

    const profile: Profile = {
      fullName:        fullName.trim(),
      sexGender,
      location:        location.trim(),
      conditions:      noneCondition ? [] : conditions,
      allergies:       noneAllergy   ? [] : allergies,
      profileComplete: true,
    };

    try {
      localStorage.setItem("userProfile", JSON.stringify(profile));
    } catch {
      // Ignore localStorage errors in restricted environments.
    }

    setSubmitted(profile);
  };

  const handleReset = () => {
    setSubmitted(null);
    setFullName("");
    setSexGender("");
    setLocation("");
    setConditions([]);
    setAllergies([]);
    setNoneAllergy(false);
    setError("");
  };

  if (submitted) {
    return (
      <main className="profile-page">
        <div className="signup-card confirmation-card">
          <p className="eyebrow">Profile ready</p>

          {submitted.fullName && (
            <>
              <div className="avatar-circle">
                {submitted.fullName.charAt(0).toUpperCase()}
              </div>
              <h1 className="confirmation-name">{submitted.fullName}</h1>
            </>
          )}

          {(submitted.sexGender || submitted.location) && (
            <p className="confirmation-sub">
              {[submitted.sexGender, submitted.location].filter(Boolean).join(" | ")}
            </p>
          )}

          <section className="conf-section">
            <p className="conf-label">Health conditions</p>
            <div className="conf-tags">
              {submitted.conditions.map((c) => (
                <span className="conf-tag condition-tag" key={c}>{c}</span>
              ))}
            </div>
          </section>

          <section className="conf-section">
            <p className="conf-label">Allergies</p>
            {submitted.allergies.length > 0 ? (
              <div className="conf-tags">
                {submitted.allergies.map((a) => (
                  <span className="conf-tag allergy-tag" key={a}>{a}</span>
                ))}
              </div>
            ) : (
              <p className="conf-none">None</p>
            )}
          </section>

          <button
            className="primary-button"
            onClick={() => router.push("/chat")}
          >
            Go to assistant
          </button>

          <button
            className="secondary-button"
            style={{ marginTop: "0.5rem" }}
            onClick={handleReset}
          >
            Edit profile
          </button>
        </div>
      </main>
    );
  }

  return (
    <main className="profile-page">
      <section className="signup-card">
        <header className="intro-block">
          <p className="eyebrow">Dietary profile</p>
          <h1>Create your profile</h1>
          <p>
            Select your health conditions — the assistant uses these automatically
            to find safe dishes near you. All other fields are optional.
          </p>
        </header>

        {error && <div className="error-banner">{error}</div>}

        <form className="profile-form" onSubmit={handleSubmit} noValidate>

          {}
          <fieldset className="profile-section">
            <legend>
              Health conditions <span className="required">*</span>
            </legend>
            <p className="section-hint">Select all that apply, or choose None.</p>
            <div className="choice-grid">
              {HEALTH_CONDITIONS.map(({ id, label }) => {
                const active = !noneCondition && conditions.includes(label);
                return (
                  <button
                    type="button"
                    key={id}
                    className={`choice-pill${active ? " choice-pill--active" : ""}`}
                    onClick={() => toggleCondition(label)}
                    aria-pressed={active}
                  >
                    <span>{label}</span>
                    {active && <span className="pill-check">Selected</span>}
                  </button>
                );
              })}

              <button
                type="button"
                className={`choice-pill${noneCondition ? " choice-pill--active" : ""}`}
                onClick={selectNoneCondition}
                aria-pressed={noneCondition}
              >
                <span>None</span>
                {noneCondition && <span className="pill-check">Selected</span>}
              </button>
            </div>
          </fieldset>

          {}
          <fieldset className="profile-section">
            <legend>
              Allergies <span className="required">*</span>
            </legend>
            <p className="section-hint">Select all that apply, or choose None.</p>
            <div className="choice-grid">
              {ALLERGY_OPTIONS.map(({ id, label }) => {
                const active = !noneAllergy && allergies.includes(label);
                return (
                  <button
                    type="button"
                    key={id}
                    className={`choice-pill${active ? " choice-pill--active choice-pill--allergy" : ""}`}
                    onClick={() => toggleAllergy(label)}
                    aria-pressed={active}
                  >
                    <span>{label}</span>
                    {active && <span className="pill-check">Selected</span>}
                  </button>
                );
              })}

              <button
                type="button"
                className={`choice-pill${noneAllergy ? " choice-pill--active" : ""}`}
                onClick={selectNoneAllergy}
                aria-pressed={noneAllergy}
              >
                <span>None</span>
                {noneAllergy && <span className="pill-check">Selected</span>}
              </button>
            </div>
          </fieldset>

          {}
          <fieldset className="profile-section">
            <legend>
              Personal details <span className="optional">(optional)</span>
            </legend>

            <div className="field-stack">
              <label className="field-label" htmlFor="fullName">Full name</label>
              <input
                className="text-input"
                id="fullName"
                type="text"
                placeholder="Enter your full name"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
              />
            </div>

            <div className="two-column" style={{ marginTop: "1rem" }}>
              <div className="field-stack">
                <label className="field-label" htmlFor="sexGender">Gender or sex</label>
                <select
                  className="text-input"
                  id="sexGender"
                  value={sexGender}
                  onChange={(e) => setSexGender(e.target.value)}
                >
                  <option value="">Select an option</option>
                  <option>Female</option>
                  <option>Male</option>
                  <option>Non-binary</option>
                  <option>Prefer not to say</option>
                  <option>Self-describe</option>
                </select>
              </div>

              <div className="field-stack">
                <label className="field-label" htmlFor="location">Home address</label>
                <input
                  className="text-input"
                  id="location"
                  type="text"
                  placeholder="123 Main St, City, State"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                />
              </div>
            </div>
          </fieldset>

          <button className="primary-button" type="submit">
            Save profile
          </button>
        </form>
      </section>
    </main>
  );
}
