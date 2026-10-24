"use client";

import { PageHeader } from "@/components/common/page-header";
import { RequireStore } from "@/components/common/require-store";
import { EmployeesTab } from "@/components/team/employees-tab";
import { ShiftsTab } from "@/components/team/shifts-tab";
import { UsersTab } from "@/components/team/users-tab";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default function TeamPage() {
  return (
    <>
      <PageHeader title="Equipo" description="Cuentas de acceso, personal de la tienda y su horario semanal." />
      <RequireStore>
        {(storeId) => (
          <Tabs defaultValue="users">
            <TabsList className="mb-5">
              <TabsTrigger value="users">Usuarios</TabsTrigger>
              <TabsTrigger value="employees">Empleados</TabsTrigger>
              <TabsTrigger value="shifts">Turnos</TabsTrigger>
            </TabsList>
            <TabsContent value="users"><UsersTab key={storeId} storeId={storeId} /></TabsContent>
            <TabsContent value="employees"><EmployeesTab key={storeId} storeId={storeId} /></TabsContent>
            <TabsContent value="shifts"><ShiftsTab key={storeId} storeId={storeId} /></TabsContent>
          </Tabs>
        )}
      </RequireStore>
    </>
  );
}
