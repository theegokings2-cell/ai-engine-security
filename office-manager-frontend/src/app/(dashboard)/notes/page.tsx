"use client";

import { useState } from "react";
import { Header } from "@/components/layouts/header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Plus, Search, FileText, Pin, Trash2 } from "lucide-react";
import { useNotes, useCreateNote, useDeleteNote, useUpdateNote, Note } from "@/lib/queries/office";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";
import { format } from "date-fns";

export default function NotesPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedNote, setSelectedNote] = useState<Note | null>(null);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newContent, setNewContent] = useState("");
  const [isPinned, setIsPinned] = useState(false);
  const { toast } = useToast();

  const { data: notes = [], isLoading } = useNotes(searchQuery || undefined);
  const createNote = useCreateNote();
  const deleteNote = useDeleteNote();
  const updateNote = useUpdateNote();

  const sortedNotes = [...(notes || [])].sort((a, b) => {
    if (a.is_pinned && !b.is_pinned) return -1;
    if (!a.is_pinned && b.is_pinned) return 1;
    return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
  });

  const handleCreate = async () => {
    if (!newTitle || !newContent) {
      toast({ title: "Error", description: "Title and content are required", variant: "destructive" });
      return;
    }
    try {
      await createNote.mutateAsync({ title: newTitle, content: newContent, is_pinned: isPinned });
      toast({ title: "Success", description: "Note created" });
      setIsCreateOpen(false);
      setNewTitle("");
      setNewContent("");
      setIsPinned(false);
    } catch (error) {
      toast({ title: "Error", description: "Failed to create note", variant: "destructive" });
    }
  };

  const handleDelete = async (noteId: string) => {
    try {
      await deleteNote.mutateAsync(noteId);
      toast({ title: "Success", description: "Note deleted" });
      setSelectedNote(null);
    } catch (error) {
      toast({ title: "Error", description: "Failed to delete note", variant: "destructive" });
    }
  };

  const handleUpdatePinned = async (note: Note) => {
    try {
      await updateNote.mutateAsync({ id: note.id, data: { is_pinned: !note.is_pinned } });
    } catch (error) {
      toast({ title: "Error", description: "Failed to update note", variant: "destructive" });
    }
  };

  return (
    <>
      <Header title="Notes" />
      <div className="flex-1 flex">
        {/* Sidebar - Notes List */}
        <div className="w-80 border-r bg-card flex flex-col">
          <div className="p-4 border-b space-y-2">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search notes..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
              />
            </div>
            <Button className="w-full" onClick={() => setIsCreateOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              New Note
            </Button>
          </div>
          <div className="flex-1 overflow-auto p-2 space-y-2">
            {isLoading ? (
              <p className="text-center text-muted-foreground p-4">Loading...</p>
            ) : sortedNotes.length === 0 ? (
              <p className="text-center text-muted-foreground p-4">No notes found</p>
            ) : (
              sortedNotes.map((note) => (
                <button
                  key={note.id}
                  onClick={() => setSelectedNote(note)}
                  className={cn(
                    "w-full text-left p-3 rounded-md hover:bg-accent transition-colors",
                    selectedNote?.id === note.id && "bg-accent"
                  )}
                >
                  <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4 text-muted-foreground" />
                    <span className="font-medium truncate flex-1">{note.title}</span>
                    {note.is_pinned && <Pin className="h-3 w-3 text-primary" />}
                  </div>
                  <p className="text-sm text-muted-foreground truncate mt-1">{note.content}</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {format(new Date(note.updated_at), "MMM d, h:mm a")}
                  </p>
                </button>
              ))
            )}
          </div>
        </div>

        {/* Main Content - Note View */}
        <div className="flex-1 p-6">
          {selectedNote ? (
            <Card className="h-full">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2">
                    {selectedNote.title}
                    {selectedNote.is_pinned && <Pin className="h-4 w-4 text-primary" />}
                  </CardTitle>
                  <div className="flex gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleUpdatePinned(selectedNote)}
                    >
                      <Pin className={cn("h-4 w-4", selectedNote.is_pinned && "fill-primary")} />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-red-600"
                      onClick={() => handleDelete(selectedNote.id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <p className="whitespace-pre-wrap">{selectedNote.content}</p>
                <p className="text-xs text-muted-foreground mt-4">
                  Last updated: {format(new Date(selectedNote.updated_at), "MMMM d, yyyy 'at' h:mm a")}
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="h-full flex items-center justify-center text-muted-foreground">
              <div className="text-center">
                <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>Select a note or create a new one</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Create Note Dialog */}
      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>New Note</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="title">Title *</Label>
              <Input
                id="title"
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                placeholder="Note title"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="content">Content *</Label>
              <textarea
                id="content"
                value={newContent}
                onChange={(e) => setNewContent(e.target.value)}
                placeholder="Write your note..."
                className="w-full h-40 p-3 rounded-md border resize-none focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="pinned"
                checked={isPinned}
                onChange={(e) => setIsPinned(e.target.checked)}
                className="rounded"
              />
              <Label htmlFor="pinned">Pin this note</Label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCreateOpen(false)}>Cancel</Button>
            <Button onClick={handleCreate} disabled={createNote.isPending}>
              {createNote.isPending ? "Creating..." : "Create Note"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
