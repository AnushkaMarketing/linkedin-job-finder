import { useState } from "react";
import { ArrowRight, MapPin, Plus } from "@phosphor-icons/react";
import { api } from "./api";
import type { Preferences, Point, Mode, Salary } from "./types";
import { split, number, Field } from "./shared";
export function PreferencesForm({
  value: p,
  change,
  report,
}: {
  value: Preferences;
  change: (p: Preferences) => void;
  report: (s: string) => void;
}) {
  const [places, setPlaces] = useState<{ label: string; point: Point }[]>([]),
    [locating, setLocating] = useState(false);
  const update = (v: Partial<Preferences>) => change({ ...p, ...v });
  async function locate() {
    setLocating(true);
    try {
      setPlaces(await api("/geocode", "POST", { query: p.location }));
    } catch (e) {
      report((e as Error).message);
    } finally {
      setLocating(false);
    }
  }
  function gps() {
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        update({
          origin: {
            latitude: pos.coords.latitude,
            longitude: pos.coords.longitude,
            precision: "user",
            source: "Browser geolocation",
          },
        });
        setLocating(false);
      },
      (e) => {
        report(e.message);
        setLocating(false);
      },
      { timeout: 10000 },
    );
  }
  return (
    <>
      <Field label="Target roles" hint="Separate up to 8 roles with commas">
        <textarea
          rows={2}
          placeholder="Social media manager, Content strategist"
          value={p.roles.join(", ")}
          onChange={(e) => update({ roles: split(e.target.value) })}
        />
      </Field>
      <Field label="Your starting location">
        <div className="input-icon">
          <MapPin size={17} />
          <input
            value={p.location}
            placeholder="Sector 137, Noida"
            onChange={(e) => update({ location: e.target.value })}
          />
        </div>
      </Field>
      <div className="location-actions">
        <button className="text-button" disabled={locating} onClick={locate}>
          {locating ? "Locating…" : "Find location"}
        </button>
        <button className="text-button" disabled={locating} onClick={gps}>
          Use my location
        </button>
      </div>
      {places.length > 0 && (
        <div className="places">
          {places.map((v) => (
            <button
              key={v.label}
              onClick={() => {
                update({ origin: v.point, location: v.label });
                setPlaces([]);
              }}
            >
              {v.label}
              <ArrowRight />
            </button>
          ))}
          <small>
            © OpenStreetMap contributors · select your starting point
          </small>
        </div>
      )}
      <div className="field-pair">
        <Field label="Latitude">
          <input
            type="number"
            step="any"
            min={-90}
            max={90}
            value={p.origin?.latitude ?? ""}
            placeholder="28.50…"
            onChange={(e) =>
              update({
                origin:
                  e.target.value === ""
                    ? null
                    : {
                        latitude: Number(e.target.value),
                        longitude: p.origin?.longitude ?? 0,
                        precision: "user",
                        source: "User supplied",
                      },
              })
            }
          />
        </Field>
        <Field label="Longitude">
          <input
            type="number"
            step="any"
            min={-180}
            max={180}
            value={p.origin?.longitude ?? ""}
            placeholder="77.41…"
            onChange={(e) =>
              update({
                origin:
                  e.target.value === ""
                    ? null
                    : {
                        latitude: p.origin?.latitude ?? 0,
                        longitude: Number(e.target.value),
                        precision: "user",
                        source: "User supplied",
                      },
              })
            }
          />
        </Field>
      </div>
      <div className="range-label">
        <label htmlFor="radius">Search radius</label>
        <strong>{p.radius_km} km</strong>
      </div>
      <input
        id="radius"
        type="range"
        min={1}
        max={100}
        value={p.radius_km}
        onChange={(e) => update({ radius_km: Number(e.target.value) })}
      />
      <div className="range-ends">
        <span>1 km</span>
        <span>100 km</span>
      </div>
      <label className="check-label">
        <input
          type="checkbox"
          checked={p.strict_radius}
          onChange={(e) => update({ strict_radius: e.target.checked })}
        />
        <span>
          Only confirmed offices in radius
          <small>Straight-line distance; remote roles are exempt.</small>
        </span>
      </label>
      <fieldset className="modes">
        <legend>Work mode</legend>
        {(["on-site", "hybrid", "remote"] as Mode[]).map((m) => (
          <label key={m} className={p.work_modes.includes(m) ? "selected" : ""}>
            <input
              type="checkbox"
              checked={p.work_modes.includes(m)}
              onChange={(e) =>
                update({
                  work_modes: e.target.checked
                    ? [...p.work_modes, m]
                    : p.work_modes.filter((x) => x !== m),
                })
              }
            />
            {m === "on-site" ? "On-site" : m[0].toUpperCase() + m.slice(1)}
          </label>
        ))}
      </fieldset>
      <details className="advanced">
        <summary>
          More preferences <Plus size={16} />
        </summary>
        <Field label="Custom radius (km)">
          <input
            type="number"
            min={1}
            max={20000}
            value={p.radius_km}
            onChange={(e) => update({ radius_km: Number(e.target.value) })}
          />
        </Field>
        <Field
          label="Employment types"
          hint="Comma separated; e.g. Full-time, Contract"
        >
          <input
            value={p.employment_types.join(", ")}
            onChange={(e) =>
              update({ employment_types: split(e.target.value) })
            }
          />
        </Field>
        <div className="field-pair">
          <Field label="Experience from">
            <input
              type="number"
              min={0}
              max={70}
              value={p.experience_min ?? ""}
              placeholder="Years"
              onChange={(e) =>
                update({ experience_min: number(e.target.value) })
              }
            />
          </Field>
          <Field label="Experience to">
            <input
              type="number"
              min={0}
              max={70}
              value={p.experience_max ?? ""}
              placeholder="Years"
              onChange={(e) =>
                update({ experience_max: number(e.target.value) })
              }
            />
          </Field>
        </div>
        <Field label="Minimum salary">
          <input
            type="number"
            min={0}
            value={p.salary.minimum ?? ""}
            placeholder="Leave blank if flexible"
            onChange={(e) =>
              update({
                salary: { ...p.salary, minimum: number(e.target.value) },
              })
            }
          />
        </Field>
        <Field label="Maximum salary">
          <input
            type="number"
            min={0}
            value={p.salary.maximum ?? ""}
            placeholder="Optional upper range"
            onChange={(e) =>
              update({
                salary: { ...p.salary, maximum: number(e.target.value) },
              })
            }
          />
        </Field>
        <div className="field-pair">
          <Field label="Currency">
            <input
              maxLength={5}
              value={p.salary.currency}
              onChange={(e) =>
                update({
                  salary: {
                    ...p.salary,
                    currency: e.target.value.toUpperCase(),
                  },
                })
              }
            />
          </Field>
          <Field label="Period">
            <select
              value={p.salary.period}
              onChange={(e) =>
                update({
                  salary: {
                    ...p.salary,
                    period: e.target.value as Salary["period"],
                  },
                })
              }
            >
              <option value="year">Year</option>
              <option value="month">Month</option>
              <option value="hour">Hour</option>
            </select>
          </Field>
        </div>
        <Field label="Preferred industries">
          <input
            value={p.industries.join(", ")}
            onChange={(e) => update({ industries: split(e.target.value) })}
          />
        </Field>
        <Field label="Exclude companies">
          <input
            value={p.excluded_companies.join(", ")}
            onChange={(e) =>
              update({ excluded_companies: split(e.target.value) })
            }
          />
        </Field>
        <Field label="Maximum results">
          <input
            type="number"
            min={1}
            max={50}
            value={p.limit}
            onChange={(e) => update({ limit: Number(e.target.value) })}
          />
        </Field>
        <small>
          Unknown salary, industry and experience stay visible as unknown. Known
          salary and experience outside your ranges are excluded. Unknown work
          mode is excluded when modes are selected.
        </small>
      </details>
    </>
  );
}
