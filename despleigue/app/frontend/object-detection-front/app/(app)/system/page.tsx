"use client";

import { PageHeader } from "@/components/common/page-header";
import { ComparisonTab } from "@/components/system/comparison-tab";
import { ModelsTab } from "@/components/system/models-tab";
import { StatusTab } from "@/components/system/status-tab";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default function SystemPage() {
  return (
    <>
      <PageHeader title="System and models" description="Inference service status, model catalog, and comparison review." />
      <Tabs defaultValue="status">
        <TabsList className="mb-5">
          <TabsTrigger value="status">Status</TabsTrigger>
          <TabsTrigger value="models">Models</TabsTrigger>
          <TabsTrigger value="compare">Comparison</TabsTrigger>
        </TabsList>
        <TabsContent value="status"><StatusTab /></TabsContent>
        <TabsContent value="models"><ModelsTab /></TabsContent>
        <TabsContent value="compare"><ComparisonTab /></TabsContent>
      </Tabs>
    </>
  );
}
