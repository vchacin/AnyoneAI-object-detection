"use client";

import { PageHeader } from "@/components/common/page-header";
import { ComparisonTab } from "@/components/system/comparison-tab";
import { ModelsTab } from "@/components/system/models-tab";
import { StatusTab } from "@/components/system/status-tab";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default function SystemPage() {
  return (
    <>
      <PageHeader title="Sistema y modelos" description="Estado del servicio de inferencia, catálogo de modelos y revisión de comparaciones." />
      <Tabs defaultValue="status">
        <TabsList className="mb-5">
          <TabsTrigger value="status">Estado</TabsTrigger>
          <TabsTrigger value="models">Modelos</TabsTrigger>
          <TabsTrigger value="compare">Comparación</TabsTrigger>
        </TabsList>
        <TabsContent value="status"><StatusTab /></TabsContent>
        <TabsContent value="models"><ModelsTab /></TabsContent>
        <TabsContent value="compare"><ComparisonTab /></TabsContent>
      </Tabs>
    </>
  );
}
