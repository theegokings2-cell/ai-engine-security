"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Header } from "@/components/layouts/header";
import { portalApiClient } from "@/lib/api/client";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { FileText, Search, Calendar, Eye } from "lucide-react";
import { format, parseISO } from "date-fns";

interface PortalUser {
  id: string;
  email: string;
  full_name: string;
  role: string;
}

interface Note {
  id: string;
  title: string;
  content: string;
  updated_at: string;
}

export default function CustomerNotesPage() {
  const router = useRouter();
  const [user, setUser] = useState<PortalUser | null>(null);
  const [notes, setNotes] = useState<Note[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [selectedNote, setSelectedNote] = useState<Note | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("portal_access_token");
    if (!token) {
      router.push("/portal/login");
      return;
    }

    portalApiClient.defaults.headers.common["Authorization"] = `Bearer ${token}`;
    fetchUser();
  }, [router]);

  const fetchUser = async () => {
    try {
      const response = await portalApiClient.get("/portal/auth/me");
      setUser(response.data);
    } catch (error) {
      console.error("Failed to fetch user:", error);
      localStorage.removeItem("portal_access_token");
      router.push("/portal/login");
    }
  };

  const fetchNotes = async () => {
    if (!user) return;

    try {
      setIsLoading(true);
      const response = await portalApiClient.get("/portal/notes", {
        params: { search, limit: 100 },
      });
      setNotes(response.data.notes || []);
    } catch (error) {
      console.error("Failed to fetch notes:", error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (user) {
      fetchNotes();
    }
  }, [user, search]);

  const formatDate = (dateStr: string) => {
    return format(parseISO(dateStr), "MMM d, yyyy h:mm a");
  };

  const filteredNotes = notes.filter((note) => {
    if (!search) return true;
    const searchLower = search.toLowerCase();
    return (
      note.title.toLowerCase().includes(searchLower) ||
      note.content.toLowerCase().includes(searchLower)
    );
  });

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <>
      <Header title="My Notes" />
      <div className="flex-1 p-6">
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search notes..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9 w-64"
              />
            </div>
          </div>

          {/* Notes Grid */}
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>
          ) : filteredNotes.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <p className="text-muted-foreground mb-4">
                  {search ? "No notes found matching your search" : "No notes yet"}
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {filteredNotes.map((note) => (
                <Card key={note.id} className="group hover:shadow-md transition-shadow cursor-pointer" onClick={() => setSelectedNote(note)}>
                  <CardContent className="p-4">
                    <h3 className="font-medium line-clamp-1 mb-2">{note.title}</h3>
                    <p className="text-sm text-muted-foreground line-clamp-3 mb-3">
                      {note.content}
                    </p>
                    <div className="flex items-center gap-1 text-xs text-muted-foreground">
                      <Calendar className="h-3 w-3" />
                      <span>{formatDate(note.updated_at)}</span>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          {/* Count */}
          {filteredNotes.length > 0 && (
            <div className="mt-4 text-sm text-muted-foreground text-center">
              {filteredNotes.length} note{filteredNotes.length !== 1 ? "s" : ""}
            </div>
          )}
        </div>
      </div>

      {/* View Note Dialog */}
      {selectedNote && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setSelectedNote(null)}>
          <Card className="w-full max-w-lg mx-4 max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <CardContent className="p-6">
              <div className="flex items-center gap-3 mb-4">
                <FileText className="h-6 w-6 text-primary" />
                <h2 className="text-xl font-semibold">{selectedNote.title}</h2>
              </div>

              <div className="prose prose-sm max-w-none">
                <p className="whitespace-pre-wrap">{selectedNote.content}</p>
              </div>

              <div className="mt-4 pt-4 border-t text-sm text-muted-foreground">
                <p>Last updated: {formatDate(selectedNote.updated_at)}</p>
              </div>

              <div className="mt-6 flex justify-end">
                <Button variant="outline" onClick={() => setSelectedNote(null)}>Close</Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </>
  );
}
