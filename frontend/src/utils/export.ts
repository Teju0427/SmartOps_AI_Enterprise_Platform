import Papa from "papaparse";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";

/**
 * Export any array of real, already-fetched data objects as a CSV file.
 * No fabricated data - callers pass exactly what's on screen.
 */
export function exportToCSV(filename: string, rows: Record<string, unknown>[]) {
  if (rows.length === 0) {
    alert("No data available to export.");
    return;
  }
  const csv = Papa.unparse(rows);
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${filename}.csv`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

interface PDFExportOptions {
  title: string;
  subtitle?: string;
  columns: string[];
  rows: (string | number)[][];
  filename: string;
}

/**
 * Export a real data table as a formatted PDF - used for Reports page
 * and any table export action. Always operates on data already retrieved
 * from the backend, never placeholder content.
 */
export function exportToPDF({ title, subtitle, columns, rows, filename }: PDFExportOptions) {
  const doc = new jsPDF({ orientation: rows.length && columns.length > 6 ? "landscape" : "portrait" });

  doc.setFontSize(16);
  doc.setTextColor(15, 42, 71);
  doc.text(title, 14, 18);

  if (subtitle) {
    doc.setFontSize(10);
    doc.setTextColor(91, 107, 130);
    doc.text(subtitle, 14, 25);
  }

  doc.setFontSize(8);
  doc.setTextColor(150, 150, 150);
  doc.text(`Generated ${new Date().toLocaleString()}`, 14, subtitle ? 31 : 25);

  autoTable(doc, {
    head: [columns],
    body: rows,
    startY: subtitle ? 36 : 30,
    headStyles: { fillColor: [31, 78, 140], textColor: 255, fontStyle: "bold", fontSize: 8 },
    bodyStyles: { fontSize: 7.5, textColor: [22, 35, 58] },
    alternateRowStyles: { fillColor: [244, 246, 249] },
    margin: { left: 14, right: 14 },
  });

  doc.save(`${filename}.pdf`);
}

/**
 * Fetches ALL records across multiple pages from a paginated endpoint,
 * respecting the backend's max page_size of 200 per request. Used
 * anywhere a full dataset is needed (exports, reports) since a single
 * oversized page_size request is rejected by the API with a 422.
 */
export async function fetchAllPages<T>(
  fetchPage: (page: number, pageSize: number) => Promise<{ items: T[]; total: number }>
): Promise<T[]> {
  const PAGE_SIZE = 200;
  const first = await fetchPage(1, PAGE_SIZE);
  const allItems = [...first.items];
  const totalPages = Math.ceil(first.total / PAGE_SIZE);

  for (let page = 2; page <= totalPages; page++) {
    const next = await fetchPage(page, PAGE_SIZE);
    allItems.push(...next.items);
  }

  return allItems;
}
