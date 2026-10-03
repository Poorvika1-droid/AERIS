"use client";

import { useEffect, useRef } from "react";
import * as maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
maplibregl.setWorkerUrl("/maplibre/maplibre-gl-worker.mjs");
export type MapPoint = {
  id: string;
  lat: number;
  lon: number;
  value?: number;
  color?: string;
  label?: string;
  extra?: string;
};

export function IndiaMap({ points, onSelect }: { points: MapPoint[]; onSelect?: (id: string) => void }) {
  const ref = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);

  useEffect(() => {
    if (!ref.current || mapRef.current) return;
    const map = new maplibregl.Map({
      container: ref.current,
      // OpenFreeMap's public Liberty style works directly with MapLibre and
      // does not require a CARTO/API token. It includes the required OSM
      // attribution in the rendered map.
      style: "https://tiles.openfreemap.org/styles/liberty",
      center: [78.96, 22.5],
      zoom: 4.1,
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const markers: maplibregl.Marker[] = [];
    const add = () => {
      for (const p of points) {
        if (p.lat == null || p.lon == null) continue;
        const el = document.createElement("div");
        el.style.width = "10px";
        el.style.height = "10px";
        el.style.borderRadius = "99px";
        el.style.background = p.color || "#22d3ee";
        el.style.boxShadow = "0 0 0 3px rgba(34,211,238,0.25)";
        el.style.cursor = "pointer";
        const marker = new maplibregl.Marker({ element: el }).setLngLat([p.lon, p.lat]).addTo(map);
        if (p.label) {
          marker.setPopup(new maplibregl.Popup({ offset: 8 }).setHTML(`<strong>${p.label}</strong><div>${p.extra ?? (p.value ?? "")}</div>`));
        }
        el.addEventListener("click", () => onSelect?.(p.id));
        markers.push(marker);
      }
    };
    if (map.loaded()) add();
    else map.once("load", add);
    return () => {
      markers.forEach((m) => m.remove());
    };
  }, [points, onSelect]);

  return <div ref={ref} className="h-[420px] w-full overflow-hidden rounded-lg border border-cyan-900/30" />;
}
