"use client";

import { useEffect, useRef, useState } from "react";

interface Props {
  onSelect: (address: string) => void;
  onCancel: () => void;
}

const API_KEY = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY ?? "";
const MAPS_SCRIPT_ID = "google-maps-js";
let mapsLoadPromise: Promise<void> | null = null;

function loadMapsScript(): Promise<void> {
  if (typeof window === "undefined") {
    return Promise.resolve();
  }

  if ((window as any).google?.maps) {
    return Promise.resolve();
  }

  if (mapsLoadPromise) {
    return mapsLoadPromise;
  }

  mapsLoadPromise = new Promise<void>((resolve, reject) => {
    const existing = document.getElementById(MAPS_SCRIPT_ID);
    if (existing) {
      existing.addEventListener("load", () => resolve(), { once: true });
      existing.addEventListener(
        "error",
        () => {
          mapsLoadPromise = null;
          reject();
        },
        { once: true }
      );
      return;
    }

    const script = document.createElement("script");
    script.id = MAPS_SCRIPT_ID;
    script.src = `https://maps.googleapis.com/maps/api/js?key=${API_KEY}&v=weekly&loading=async`;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => {
      mapsLoadPromise = null;
      reject();
    };

    document.head.appendChild(script);
  });

  return mapsLoadPromise;
}

export default function GoogleAddressInput({ onSelect, onCancel }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [selectedAddress, setSelectedAddress] = useState("");
  const [selectedDisplay, setSelectedDisplay] = useState("");

  useEffect(() => {
    const host = containerRef.current;

    if (!API_KEY || !host) {
      return;
    }

    const container: HTMLDivElement = host;

    let cancelled = false;
    let placeAutocomplete: any = null;

    async function initMap() {
      await loadMapsScript();
      if (cancelled) {
        return;
      }

      const g = (window as any).google;
      const { PlaceAutocompleteElement } = await g.maps.importLibrary("places");
      if (cancelled) {
        return;
      }

      placeAutocomplete = new PlaceAutocompleteElement({});
      placeAutocomplete.style.width = "100%";

      container.appendChild(placeAutocomplete);

      placeAutocomplete.addEventListener("gmp-select", async ({ placePrediction }: any) => {
        const place = placePrediction.toPlace();
        await place.fetchFields({
          fields: ["displayName", "formattedAddress", "location"],
        });

        const addr: string = place.formattedAddress ?? place.displayName ?? "";
        setSelectedAddress(addr);
        setSelectedDisplay(place.displayName ?? addr);
      });
    }

    initMap().catch(() => {
    });

    return () => {
      cancelled = true;
      if (placeAutocomplete && container.contains(placeAutocomplete)) {
        container.removeChild(placeAutocomplete);
      }
    };
  }, []);

  return (
    <div className="gaddr-overlay" role="dialog" aria-modal="true" aria-label="Set search address">
      <div className="gaddr-modal">
        <div className="gaddr-header">
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <circle cx="12" cy="10" r="3" />
            <path d="M12 2a8 8 0 0 1 8 8c0 5.25-8 13-8 13S4 15.25 4 10a8 8 0 0 1 8-8z" />
          </svg>
          <span>Set Search Address</span>
          <button className="gaddr-close" onClick={onCancel} aria-label="Close">
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <div className="gaddr-search-area">
          <div ref={containerRef} className="gaddr-autocomplete-container" />
        </div>

        <div className="gaddr-footer">
          <span className="gaddr-selected-addr">
            {selectedAddress ? (
              <>
                <strong>{selectedDisplay}</strong>
                {selectedDisplay !== selectedAddress && <>, {selectedAddress}</>}
              </>
            ) : (
              "Choose a result from search above."
            )}
          </span>
          <button
            className="primary-button"
            onClick={() => onSelect(selectedAddress)}
            disabled={!selectedAddress}
          >
            Set address
          </button>
        </div>
      </div>
    </div>
  );
}
