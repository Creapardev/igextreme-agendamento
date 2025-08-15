import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Calendar, Clock, User, MapPin, Phone, CheckCircle, Settings } from 'lucide-react';
import { Button } from './components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card';
import { Input } from './components/ui/input';
import { Label } from './components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { Badge } from './components/ui/badge';
import { Alert, AlertDescription } from './components/ui/alert';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from './components/ui/dialog';
import { Calendar as CalendarComponent } from './components/ui/calendar';
import { Textarea } from './components/ui/textarea';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

function App() {
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [availableSlots, setAvailableSlots] = useState([]);
  const [appointments, setAppointments] = useState([]);
  const [selectedSlot, setSelectedSlot] = useState(null);
  const [bookingForm, setBookingForm] = useState({
    clientName: '',
    whatsapp: '',
    notes: ''
  });
  const [loading, setLoading] = useState(false);
  const [notification, setNotification] = useState(null);
  const [isAdmin, setIsAdmin] = useState(false);
  const [newSlotForm, setNewSlotForm] = useState({
    date: '',
    time: '',
    type: 'appointment'
  });

  useEffect(() => {
    if (selectedDate) {
      fetchAvailableSlots();
      fetchAppointments();
    }
  }, [selectedDate]);

  const fetchAvailableSlots = async () => {
    try {
      const dateStr = selectedDate.toISOString().split('T')[0];
      const response = await axios.get(`${BACKEND_URL}/api/available-slots?date=${dateStr}`);
      setAvailableSlots(response.data);
    } catch (error) {
      console.error('Error fetching slots:', error);
    }
  };

  const fetchAppointments = async () => {
    try {
      const dateStr = selectedDate.toISOString().split('T')[0];
      const response = await axios.get(`${BACKEND_URL}/api/appointments?date=${dateStr}`);
      setAppointments(response.data);
    } catch (error) {
      console.error('Error fetching appointments:', error);
    }
  };

  const handleDateSelect = async (date) => {
    if (date) {
      setSelectedDate(date);
      setSelectedSlot(null);
      setLoading(true);
      try {
        const dateStr = date.toISOString().split('T')[0];
        const response = await axios.get(`${BACKEND_URL}/api/available-slots?date=${dateStr}`);
        setAvailableSlots(response.data);
        
        const appointmentsResponse = await axios.get(`${BACKEND_URL}/api/appointments?date=${dateStr}`);
        setAppointments(appointmentsResponse.data);
      } catch (error) {
        console.error('Error fetching data:', error);
        setNotification({ type: 'error', message: 'Erro ao carregar dados para esta data.' });
      }
      setLoading(false);
    }
  };

  const handleBooking = async () => {
    if (!selectedSlot || !bookingForm.clientName || !bookingForm.whatsapp) {
      setNotification({ type: 'error', message: 'Por favor, preencha todos os campos obrigatórios.' });
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post(`${BACKEND_URL}/api/appointments`, {
        slot_id: selectedSlot.id,
        client_name: bookingForm.clientName,
        whatsapp: bookingForm.whatsapp,
        notes: bookingForm.notes,
        date: selectedSlot.date,
        time: selectedSlot.time
      });

      setNotification({ 
        type: 'success', 
        message: 'Agendamento confirmado! Você receberá uma confirmação em breve.' 
      });
      
      setBookingForm({ clientName: '', whatsapp: '', notes: '' });
      setSelectedSlot(null);
      fetchAvailableSlots();
      fetchAppointments();
    } catch (error) {
      setNotification({ 
        type: 'error', 
        message: 'Erro ao criar agendamento. Tente novamente.' 
      });
    }
    setLoading(false);
  };

  const handleCreateSlot = async () => {
    if (!newSlotForm.date || !newSlotForm.time) return;

    try {
      await axios.post(`${BACKEND_URL}/api/available-slots`, newSlotForm);
      setNotification({ type: 'success', message: 'Horário criado com sucesso!' });
      setNewSlotForm({ date: '', time: '', type: 'appointment' });
      fetchAvailableSlots();
    } catch (error) {
      setNotification({ type: 'error', message: 'Erro ao criar horário.' });
    }
  };

  const formatTime = (time) => {
    return time.substring(0, 5);
  };

  const formatDate = (date) => {
    return new Date(date).toLocaleDateString('pt-BR');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-indigo-600 rounded-lg flex items-center justify-center">
                <Calendar className="h-6 w-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Creapar</h1>
                <p className="text-sm text-gray-600">Sistema de Agendamento</p>
              </div>
            </div>
            <Button
              variant={isAdmin ? "default" : "outline"}
              onClick={() => setIsAdmin(!isAdmin)}
              className="flex items-center space-x-2"
            >
              <Settings className="h-4 w-4" />
              <span>{isAdmin ? 'Modo Cliente' : 'Modo Admin'}</span>
            </Button>
          </div>
        </div>
      </header>

      {notification && (
        <Alert className={`max-w-2xl mx-auto mt-4 ${notification.type === 'error' ? 'border-red-200 bg-red-50' : 'border-green-200 bg-green-50'}`}>
          <AlertDescription className={notification.type === 'error' ? 'text-red-800' : 'text-green-800'}>
            {notification.message}
          </AlertDescription>
        </Alert>
      )}

      <div className="max-w-7xl mx-auto px-4 py-8">
        {!isAdmin ? (
          /* Cliente View */
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Hero Section */}
            <div className="lg:col-span-2 mb-8">
              <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-indigo-600 to-purple-700 p-8 text-white">
                <div className="relative z-10">
                  <h2 className="text-3xl font-bold mb-4">Agende seu Horário</h2>
                  <p className="text-xl opacity-90 mb-6">Escolha o melhor horário para você. Duração: 30 minutos cada sessão.</p>
                  <div className="flex items-center space-x-6 text-sm">
                    <div className="flex items-center space-x-2">
                      <Clock className="h-5 w-5" />
                      <span>30 min por sessão</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <CheckCircle className="h-5 w-5" />
                      <span>Confirmação automática</span>
                    </div>
                  </div>
                </div>
                <div className="absolute top-0 right-0 w-1/3 h-full opacity-20">
                  <img 
                    src="https://images.unsplash.com/photo-1642360912445-61d71dd98400?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1Nzl8MHwxfHNlYXJjaHwxfHxwcm9mZXNzaW9uYWwlMjBzY2hlZHVsaW5nfGVufDB8fHx8MTc1NTI4MjcxNXww&ixlib=rb-4.1.0&q=85"
                    alt="Calendar Interface"
                    className="w-full h-full object-cover rounded-lg"
                  />
                </div>
              </div>
            </div>

            {/* Calendar */}
            <Card className="shadow-lg">
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Calendar className="h-5 w-5" />
                  <span>Selecione uma Data</span>
                </CardTitle>
                <CardDescription>
                  Escolha o dia que você gostaria de agendar
                </CardDescription>
              </CardHeader>
              <CardContent>
                <CalendarComponent
                  mode="single"
                  selected={selectedDate}
                  onSelect={handleDateSelect}
                  disabled={(date) => date < new Date(new Date().toDateString())}
                  className="rounded-md border w-full"
                />
              </CardContent>
            </Card>

            {/* Available Slots */}
            <Card className="shadow-lg">
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Clock className="h-5 w-5" />
                  <span>Horários Disponíveis</span>
                </CardTitle>
                <CardDescription>
                  {formatDate(selectedDate)} - Clique em um horário para agendar
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-3">
                  {availableSlots.length > 0 ? (
                    availableSlots.map((slot) => (
                      <Button
                        key={slot.id}
                        variant={selectedSlot?.id === slot.id ? "default" : "outline"}
                        onClick={() => setSelectedSlot(slot)}
                        className="h-12 text-sm font-medium"
                      >
                        {formatTime(slot.time)}
                      </Button>
                    ))
                  ) : (
                    <div className="col-span-2 text-center py-8 text-gray-500">
                      Nenhum horário disponível para esta data
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Booking Form */}
            {selectedSlot && (
              <Card className="lg:col-span-2 shadow-lg border-indigo-200">
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <User className="h-5 w-5" />
                    <span>Confirmar Agendamento</span>
                  </CardTitle>
                  <CardDescription>
                    Horário selecionado: {formatDate(selectedSlot.date)} às {formatTime(selectedSlot.time)}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="clientName">Nome Completo *</Label>
                      <Input
                        id="clientName"
                        value={bookingForm.clientName}
                        onChange={(e) => setBookingForm({...bookingForm, clientName: e.target.value})}
                        placeholder="Seu nome completo"
                        className="mt-1"
                      />
                    </div>
                    <div>
                      <Label htmlFor="whatsapp">WhatsApp *</Label>
                      <Input
                        id="whatsapp"
                        value={bookingForm.whatsapp}
                        onChange={(e) => setBookingForm({...bookingForm, whatsapp: e.target.value})}
                        placeholder="(11) 99999-9999"
                        className="mt-1"
                      />
                    </div>
                  </div>
                  <div>
                    <Label htmlFor="notes">Observações (opcional)</Label>
                    <Textarea
                      id="notes"
                      value={bookingForm.notes}
                      onChange={(e) => setBookingForm({...bookingForm, notes: e.target.value})}
                      placeholder="Alguma informação adicional..."
                      className="mt-1"
                      rows={3}
                    />
                  </div>
                  <Button
                    onClick={handleBooking}
                    disabled={loading}
                    className="w-full bg-indigo-600 hover:bg-indigo-700 text-white py-3 text-lg font-medium"
                  >
                    {loading ? 'Agendando...' : 'Confirmar Agendamento'}
                  </Button>
                </CardContent>
              </Card>
            )}
          </div>
        ) : (
          /* Admin View */
          <Tabs defaultValue="appointments" className="w-full">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="appointments">Agendamentos</TabsTrigger>
              <TabsTrigger value="slots">Gerenciar Horários</TabsTrigger>
              <TabsTrigger value="calendar">Calendário</TabsTrigger>
            </TabsList>

            <TabsContent value="appointments" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Agendamentos do Dia</CardTitle>
                  <CardDescription>{formatDate(selectedDate)}</CardDescription>
                </CardHeader>
                <CardContent>
                  {appointments.length > 0 ? (
                    <div className="space-y-4">
                      {appointments.map((appointment) => (
                        <div key={appointment.id} className="flex items-center justify-between p-4 border rounded-lg">
                          <div className="flex items-center space-x-4">
                            <div className="w-12 h-12 bg-indigo-100 rounded-full flex items-center justify-center">
                              <User className="h-6 w-6 text-indigo-600" />
                            </div>
                            <div>
                              <h3 className="font-medium">{appointment.client_name}</h3>
                              <p className="text-sm text-gray-600 flex items-center space-x-2">
                                <Phone className="h-4 w-4" />
                                <span>{appointment.whatsapp}</span>
                              </p>
                              {appointment.notes && (
                                <p className="text-sm text-gray-500 mt-1">{appointment.notes}</p>
                              )}
                            </div>
                          </div>
                          <div className="text-right">
                            <Badge variant="outline">{formatTime(appointment.time)}</Badge>
                            <p className="text-sm text-gray-600 mt-1">30 min</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-8 text-gray-500">
                      Nenhum agendamento para esta data
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="slots" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Criar Novo Horário</CardTitle>
                  <CardDescription>Adicione horários disponíveis para agendamento</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <Label htmlFor="date">Data</Label>
                      <Input
                        id="date"
                        type="date"
                        value={newSlotForm.date}
                        onChange={(e) => setNewSlotForm({...newSlotForm, date: e.target.value})}
                        className="mt-1"
                      />
                    </div>
                    <div>
                      <Label htmlFor="time">Horário</Label>
                      <Input
                        id="time"
                        type="time"
                        value={newSlotForm.time}
                        onChange={(e) => setNewSlotForm({...newSlotForm, time: e.target.value})}
                        className="mt-1"
                      />
                    </div>
                    <div className="flex items-end">
                      <Button onClick={handleCreateSlot} className="w-full">
                        Criar Horário
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="calendar" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Calendário Administrativo</CardTitle>
                  <CardDescription>Visualização geral dos agendamentos</CardDescription>
                </CardHeader>
                <CardContent>
                  <CalendarComponent
                    mode="single"
                    selected={selectedDate}
                    onSelect={setSelectedDate}
                    className="rounded-md border w-full"
                  />
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        )}
      </div>
    </div>
  );
}

export default App;